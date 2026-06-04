"""
Reins Server - Workflow 执行引擎

实现 WorkflowEngine.execute(workflow_id) — 加载Workflow+Steps，
用DAGScheduler按依赖顺序调度，支持并行执行。

功能：
- pause/resume/cancel
- tracker.py 事件集成
"""

import asyncio
from loguru import logger
import time
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any, Awaitable
from concurrent.futures import ThreadPoolExecutor
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    SqlWorkflow, SqlWorkflowStep,
    WorkflowStatus, WorkflowStepStatus,
)
from models.workflow import WorkflowStepResponse
from persistence.database import DatabaseManager
from persistence.repository import WorkflowRepository, WorkflowStepRepository
from reins.core.assignment import get_agent_registry, get_task_assigner

# ============================================================================
# 执行状态
# ============================================================================

class ExecutionState(str, Enum):
    """工作流执行状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

# ============================================================================
# 执行引擎
# ============================================================================

class WorkflowExecutionEngine:
    """
    工作流执行引擎
    
    负责：
    - 从数据库加载 Workflow + Steps
    - DAG 调度与并行执行
    - pause/resume/cancel
    - tracker.py 事件集成
    """
    
    def __init__(self, db_manager: DatabaseManager, max_concurrency: int = 4):
        """
        :param db_manager: 数据库管理器
        :param max_concurrency: 最大并发任务数
        """
        self._db_manager = db_manager
        self._engine = db_manager.engine
        self._Session = sessionmaker(bind=self._engine)
        
        self.max_concurrency = max_concurrency
        self._executor = ThreadPoolExecutor(max_workers=max_concurrency)
        
        # 执行状态
        self._execution_state: ExecutionState = ExecutionState.IDLE
        self._execution_lock = asyncio.Lock()
        
        # 正在执行的任务
        self._running_steps: Dict[str, asyncio.Task] = {}
        self._completed_step_ids: Set[str] = set()
        self._failed_step_ids: Set[str] = set()
        self._cancelled_step_ids: Set[str] = set()
        
        # Pause 控制
        self._paused_event = asyncio.Event()
        self._paused_event.set()  # 默认不暂停
        
        # Tracker 回调（外部注入）
        self._tracker_callback: Optional[Callable] = None
        
        # 步骤执行器映射（外部提供）
        self._step_executors: Dict[str, Callable[[SqlWorkflowStep], Awaitable[dict]]] = {}
        
        # 当前执行的 workflow_id
        self._current_workflow_id: Optional[str] = None
        
        # 指标
        self._total_steps = 0
        self._completed_steps = 0
        self._failed_steps = 0
    
    def set_tracker(self, tracker_callback: Callable[[dict], None]):
        """
        设置 tracker 回调函数
        
        :param tracker_callback: 事件回调，接收 dict 包含 event_type, step_id, workflow_id, data
        """
        self._tracker_callback = tracker_callback
    
    def set_step_executor(self, step_id: str, executor: Callable[[SqlWorkflowStep], Awaitable[dict]]):
        """设置步骤执行器"""
        self._step_executors[step_id] = executor
    
    def set_default_executor(self, executor: Callable[[SqlWorkflowStep], Awaitable[dict]]):
        """设置默认步骤执行器（用于所有未单独设置执行器的步骤）"""
        self._default_executor = executor
    
    def _emit_event(self, event_type: str, step_id: str, data: dict = None):
        """发送 tracker 事件"""
        if self._tracker_callback:
            try:
                self._tracker_callback({
                    "event_type": event_type,
                    "step_id": step_id,
                    "workflow_id": self._current_workflow_id,
                    "data": data or {},
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"Tracker callback error: {e}")
    
    def _get_repositories(self):
        """获取仓库会话"""
        session = self._Session()
        workflow_repo = WorkflowRepository(self._engine)
        step_repo = WorkflowStepRepository(self._engine)
        return session, workflow_repo, step_repo
    
    async def execute(self, workflow_id: str) -> dict:
        """
        执行工作流
        
        :param workflow_id: 工作流 ID
        :return: 执行结果
        """
        async with self._execution_lock:
            if self._execution_state == ExecutionState.RUNNING:
                raise RuntimeError(f"Workflow {workflow_id} is already running")
            
            self._execution_state = ExecutionState.RUNNING
            self._current_workflow_id = workflow_id
            self._running_steps.clear()
            self._completed_step_ids.clear()
            self._failed_step_ids.clear()
            self._cancelled_step_ids.clear()
            self._paused_event.set()
        
        session, workflow_repo, step_repo = self._get_repositories()
        
        try:
            # 加载工作流
            workflow = workflow_repo.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {workflow_id}")
            
            # 加载步骤
            steps = step_repo.list_by_workflow(workflow_id)
            if not steps:
                raise ValueError(f"No steps found for workflow: {workflow_id}")
            
            self._total_steps = len(steps)
            
            # 更新工作流状态为 RUNNING
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now()
            workflow_repo.save(workflow)
            session.commit()
            
            self._emit_event("workflow_started", "", {
                "workflow_id": workflow_id,
                "total_steps": self._total_steps,
            })
            
            # 构建 DAG
            dag = self._build_dag(steps)
            
            # 检查循环依赖
            cycle = self._detect_cycle(dag)
            if cycle:
                raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)}")
            
            # 获取并行执行组
            parallel_groups = self._get_parallel_groups(dag, steps)
            
            # 执行每一层
            for group_idx, group in enumerate(parallel_groups):
                # 检查是否暂停
                await self._paused_event.wait()
                
                # 检查是否取消
                if self._execution_state == ExecutionState.CANCELLED:
                    await self._handle_cancellation(workflow, workflow_repo, step_repo, session)
                    return self._build_result(workflow_id, False, "Cancelled")
                
                logger.info(f"Executing parallel group {group_idx + 1}: {[s.id for s in group]}")
                
                # 并行执行当前组
                await self._execute_parallel_group(group, step_repo, session)
                
                # 检查是否有失败
                if self._failed_step_ids:
                    # 标记依赖失败步骤的步骤为 blocked
                    await self._mark_blocked_dependents(steps, step_repo, session)
            
            # 判断执行结果
            success = len(self._failed_step_ids) == 0
            
            if success:
                self._execution_state = ExecutionState.COMPLETED
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                self._emit_event("workflow_completed", "", {"workflow_id": workflow_id})
            else:
                self._execution_state = ExecutionState.FAILED
                workflow.status = WorkflowStatus.FAILED
                self._emit_event("workflow_failed", "", {
                    "workflow_id": workflow_id,
                    "failed_steps": list(self._failed_step_ids),
                })
            
            workflow_repo.save(workflow)
            session.commit()
            
            return self._build_result(workflow_id, success)
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            self._execution_state = ExecutionState.FAILED
            
            # 更新工作流状态
            try:
                workflow = workflow_repo.get(workflow_id)
                if workflow:
                    workflow.status = WorkflowStatus.FAILED
                    workflow_repo.save(workflow)
                    session.commit()
            except Exception:
                pass
            
            self._emit_event("workflow_error", "", {
                "workflow_id": workflow_id,
                "error": str(e),
            })
            
            return self._build_result(workflow_id, False, str(e))
        
        finally:
            session.close()
    
    async def pause(self):
        """暂停工作流执行"""
        if self._execution_state != ExecutionState.RUNNING:
            raise RuntimeError("Cannot pause: workflow is not running")
        
        logger.info("Pausing workflow execution")
        self._paused_event.clear()
        self._execution_state = ExecutionState.PAUSED
        self._emit_event("workflow_paused", "", {
            "workflow_id": self._current_workflow_id,
        })
    
    async def resume(self):
        """恢复工作流执行"""
        if self._execution_state != ExecutionState.PAUSED:
            raise RuntimeError("Cannot resume: workflow is not paused")
        
        logger.info("Resuming workflow execution")
        self._execution_state = ExecutionState.RUNNING
        self._paused_event.set()
        self._emit_event("workflow_resumed", "", {
            "workflow_id": self._current_workflow_id,
        })
    
    async def cancel(self):
        """取消工作流执行"""
        if self._execution_state not in (ExecutionState.RUNNING, ExecutionState.PAUSED):
            raise RuntimeError("Cannot cancel: workflow is not running or paused")
        
        logger.info("Cancelling workflow execution")
        self._execution_state = ExecutionState.CANCELLED
        
        # 取消所有运行中的任务
        for step_id, task in list(self._running_steps.items()):
            task.cancel()
            self._cancelled_step_ids.add(step_id)
        
        self._paused_event.set()  # 解除暂停等待
        
        self._emit_event("workflow_cancelled", "", {
            "workflow_id": self._current_workflow_id,
        })
    
    async def add_step(self, workflow_id: str, step_data: dict, dependencies: List[str] = None,
                       insert_position: str = "append") -> SqlWorkflowStep:
        """
        动态添加步骤（在执行中插入新步骤）
        
        :param workflow_id: 工作流 ID
        :param step_data: 步骤数据
        :param dependencies: 依赖的步骤 ID 列表
        :param insert_position: 插入位置 - "append"(末尾), "front"(前置), "after:<step_id>"(某步骤之后)
        :return: 创建的步骤
        """
        async with self._execution_lock:
            session, workflow_repo, step_repo = self._get_repositories()
            
            try:
                # 获取现有步骤
                existing_steps = step_repo.list_by_workflow(workflow_id)
                
                # 确定插入位置
                if insert_position == "front" and existing_steps:
                    # 前置插入：所有现有步骤的order+1
                    for step in existing_steps:
                        step.order = (step.order or 0) + 1
                        step_repo.save(step)
                    new_order = 1
                elif insert_position.startswith("after:"):
                    # 插入到指定步骤之后
                    after_step_id = insert_position[6:]
                    after_step = next((s for s in existing_steps if s.id == after_step_id), None)
                    if not after_step:
                        raise ValueError(f"Step not found: {after_step_id}")
                    # 将>=after_order的步骤order+1
                    for step in existing_steps:
                        if (step.order or 0) >= (after_step.order or 0):
                            step.order = (step.order or 0) + 1
                            step_repo.save(step)
                    new_order = (after_step.order or 0) + 1
                else:
                    # 默认追加到最后
                    new_order = max([s.order or 0 for s in existing_steps], default=0) + 1
                
                # 自动分配Agent（如果未指定）
                agent_id = step_data.get("agent_id")
                if not agent_id:
                    # 使用TaskAssigner自动分配
                    assigner = get_task_assigner()
                    # 创建临时step对象用于分配
                    class TempStep:
                        def __init__(self, data):
                            self.id = data.get("id", str(uuid.uuid4()))
                            self.name = data.get("name", "New Step")
                            self.description = data.get("description")
                            self.input_data = data.get("input_data", {})
                            self.capabilities = data.get("capabilities", [])
                            self.agent_id = None
                    temp_step = TempStep(step_data)
                    agent_id = assigner.assign(temp_step)
                
                # 创建新步骤
                new_step = SqlWorkflowStep(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow_id,
                    name=step_data.get("name", "New Step"),
                    description=step_data.get("description"),
                    status=WorkflowStepStatus.PENDING,
                    dependencies=dependencies or [],
                    order=new_order,
                    agent_id=agent_id,
                    input_data=step_data.get("input_data", {}),
                    max_retries=step_data.get("max_retries", 3),
                    timeout_seconds=step_data.get("timeout_seconds"),
                )
                
                # 如果是在工作流执行过程中添加，需要处理DAG
                if self._execution_state == ExecutionState.RUNNING:
                    # 将新步骤加入待执行集合（如果依赖都满足了）
                    pass  # DAG会在下一轮调度时处理
                
                step_repo.save(new_step)
                session.commit()
                
                self._emit_event("step_added", new_step.id, {
                    "workflow_id": workflow_id,
                    "step_name": new_step.name,
                    "dependencies": dependencies,
                    "insert_position": insert_position,
                    "agent_id": agent_id,
                })
                
                logger.info(f"Added step {new_step.id} to workflow {workflow_id} at order {new_order}")
                return new_step
            
            finally:
                session.close()
    
    def _build_dag(self, steps: List[SqlWorkflowStep]) -> Dict[str, Set[str]]:
        """构建 DAG（step_id -> dependencies）"""
        dag: Dict[str, Set[str]] = defaultdict(set)
        
        for step in steps:
            deps = step.dependencies or []
            dag[step.id] = set(deps)
        
        return dag
    
    def _detect_cycle(self, dag: Dict[str, Set[str]]) -> Optional[List[str]]:
        """检测循环依赖"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = defaultdict(int)
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            color[node] = GRAY
            
            for neighbor in dag.get(node, []):
                if color.get(neighbor, 0) == GRAY:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
                elif color.get(neighbor, 0) == WHITE:
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
            
            color[node] = BLACK
            return None
        
        for node in dag:
            if color.get(node, 0) == WHITE:
                cycle = dfs(node, [node])
                if cycle:
                    return cycle
        
        return None
    
    def _get_parallel_groups(self, dag: Dict[str, Set[str]], steps: List[SqlWorkflowStep]) -> List[List[SqlWorkflowStep]]:
        """将步骤分组为并行执行层"""
        step_map = {s.id: s for s in steps}
        groups: List[List[SqlWorkflowStep]] = []
        remaining = set(step_map.keys())
        completed: Set[str] = set()
        
        while remaining:
            # 找到所有依赖都已完成的步骤
            layer = []
            for step_id in remaining:
                deps = dag.get(step_id, set())
                if deps.issubset(completed):
                    layer.append(step_map[step_id])
            
            if not layer:
                raise ValueError("Cannot group steps: possible circular dependency")
            
            groups.append(layer)
            for step in layer:
                completed.add(step.id)
                remaining.remove(step.id)
        
        return groups
    
    async def _execute_parallel_group(self, group: List[SqlWorkflowStep], 
                                      step_repo: WorkflowStepRepository,
                                      session) -> None:
        """并行执行一组步骤"""
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async def execute_with_semaphore(step: SqlWorkflowStep):
            async with semaphore:
                if self._execution_state == ExecutionState.CANCELLED:
                    return
                await self._execute_step(step, step_repo, session)
        
        await asyncio.gather(*[execute_with_semaphore(step) for step in group])
    
    async def _execute_step(self, step: SqlWorkflowStep,
                            step_repo: WorkflowStepRepository,
                            session) -> None:
        """执行单个步骤"""
        step_id = step.id
        
        # 自动分配Agent（如果未指定）
        if not step.agent_id:
            assigner = get_task_assigner()
            agent_id = assigner.assign(step)
            if agent_id:
                step.agent_id = agent_id
                step_repo.save(step)
                session.commit()
        
        # 获取执行器
        executor = self._step_executors.get(step_id, getattr(self, '_default_executor', None))
        if not executor:
            logger.warning(f"No executor for step: {step_id}")
            return
        
        # 更新步骤状态为 RUNNING
        step.status = WorkflowStepStatus.RUNNING
        step.started_at = datetime.now()
        step_repo.save(step)
        session.commit()
        
        self._emit_event("step_started", step_id, {
            "step_name": step.name,
            "workflow_id": step.workflow_id,
            "agent_id": step.agent_id,
        })
        
        # 创建异步任务
        task = asyncio.create_task(self._run_step(step, executor, step_repo, session))
        self._running_steps[step_id] = task
        
        try:
            await task
        except asyncio.CancelledError:
            # 被取消
            self._cancelled_step_ids.add(step_id)
            step.status = WorkflowStepStatus.SKIPPED
            step_repo.save(step)
            session.commit()
        finally:
            self._running_steps.pop(step_id, None)
    
    async def _run_step(self, step: SqlWorkflowStep,
                       executor: Callable[[SqlWorkflowStep], Awaitable[dict]],
                       step_repo: WorkflowStepRepository,
                       session) -> None:
        """运行步骤的内部实现"""
        try:
            # 等待暂停
            await self._paused_event.wait()
            
            # 检查取消
            if self._execution_state == ExecutionState.CANCELLED:
                step.status = WorkflowStepStatus.SKIPPED
                step_repo.save(step)
                session.commit()
                return
            
            # 执行步骤
            result = await executor(step)
            
            # 成功
            step.status = WorkflowStepStatus.DONE
            step.output_data = result
            step.completed_at = datetime.now()
            self._completed_step_ids.add(step.id)
            self._completed_steps += 1
            
            self._emit_event("step_completed", step.id, {
                "step_name": step.name,
                "result": result,
            })
            
        except asyncio.CancelledError:
            step.status = WorkflowStepStatus.SKIPPED
            step.completed_at = datetime.now()
            self._cancelled_step_ids.add(step.id)
            
            self._emit_event("step_cancelled", step.id, {
                "step_name": step.name,
            })
            raise
        
        except Exception as e:
            logger.error(f"Step execution error: {step.id}, error: {e}")
            
            # 失败
            step.status = WorkflowStepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            self._failed_step_ids.add(step.id)
            self._failed_steps += 1
            
            self._emit_event("step_failed", step.id, {
                "step_name": step.name,
                "error": str(e),
            })
        
        finally:
            step_repo.save(step)
            session.commit()
    
    async def _mark_blocked_dependents(self, steps: List[SqlWorkflowStep],
                                       step_repo: WorkflowStepRepository,
                                       session) -> None:
        """标记依赖失败步骤的步骤为 blocked"""
        step_map = {s.id: s for s in steps}
        
        # 构建反向依赖图
        reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        for step in steps:
            for dep in step.dependencies or []:
                reverse_deps[dep].add(step.id)
        
        # BFS 标记 blocked
        queue = list(self._failed_step_ids)
        blocked = set()
        
        while queue:
            failed_id = queue.pop(0)
            for dependent_id in reverse_deps.get(failed_id, []):
                if dependent_id not in blocked and dependent_id not in self._completed_step_ids:
                    step = step_map.get(dependent_id)
                    if step and step.status == WorkflowStepStatus.PENDING:
                        step.status = WorkflowStepStatus.BLOCKED
                        step.error = f"Blocked due to dependency {failed_id} failure"
                        step_repo.save(step)
                        blocked.add(dependent_id)
                        queue.append(dependent_id)
        
        if blocked:
            session.commit()
            self._emit_event("steps_blocked", "", {
                "blocked_steps": list(blocked),
            })
    
    async def _handle_cancellation(self, workflow: SqlWorkflow,
                                   workflow_repo: WorkflowRepository,
                                   step_repo: WorkflowStepRepository,
                                   session) -> None:
        """处理取消后的清理"""
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()
        workflow_repo.save(workflow)
        
        # 标记所有未完成的步骤为 SKIPPED
        steps = step_repo.list_by_workflow(workflow.id)
        for step in steps:
            if step.status in (WorkflowStepStatus.PENDING, WorkflowStepStatus.RUNNING):
                step.status = WorkflowStepStatus.SKIPPED
                step.completed_at = datetime.now()
                step_repo.save(step)
        
        session.commit()
    
    def _build_result(self, workflow_id: str, success: bool, error: str = None) -> dict:
        """构建执行结果"""
        return {
            "workflow_id": workflow_id,
            "success": success,
            "error": error,
            "total_steps": self._total_steps,
            "completed_steps": self._completed_steps,
            "failed_steps": self._failed_steps,
            "cancelled_steps": len(self._cancelled_step_ids),
            "execution_state": self._execution_state.value,
        }
    
    def get_execution_state(self) -> ExecutionState:
        """获取当前执行状态"""
        return self._execution_state
    
    def get_step_status(self, step_id: str) -> Optional[str]:
        """获取步骤状态"""
        if step_id in self._completed_step_ids:
            return WorkflowStepStatus.DONE
        if step_id in self._failed_step_ids:
            return WorkflowStepStatus.FAILED
        if step_id in self._cancelled_step_ids:
            return WorkflowStepStatus.SKIPPED
        return None
    
    def shutdown(self):
        """关闭引擎"""
        self._executor.shutdown(wait=True)
        logger.info("Workflow execution engine shutdown")
