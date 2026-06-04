"""
Reins Server - 工作流引擎

实现核心功能：
- 任务状态机：定义状态流转规则
- 依赖 DAG 调度：拓扑排序 + 循环依赖检测
- 并行任务管理：并发控制 + 结果聚合
"""

import asyncio
from loguru import logger
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from concurrent.futures import ThreadPoolExecutor

# ============================================================================
# 状态机定义
# ============================================================================

class TaskState(str, Enum):
    """任务状态枚举"""
    CREATED = "created"        # 已创建
    DECOMPOSED = "decomposed"  # 已分解
    WAITING = "waiting"        # 等待依赖
    RUNNING = "running"        # 运行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 执行失败
    CANCELLED = "cancelled"    # 已取消
    
    @classmethod
    def get_valid_transitions(cls) -> Dict['TaskState', Set['TaskState']]:
        """获取状态转换规则"""
        return {
            cls.CREATED: {cls.DECOMPOSED, cls.RUNNING, cls.CANCELLED},  # 可以直接运行或先分解
            cls.DECOMPOSED: {cls.WAITING, cls.CANCELLED, cls.RUNNING},  # 分解后等待或直接运行
            cls.WAITING: {cls.RUNNING, cls.FAILED},  # 依赖失败则任务失败
            cls.RUNNING: {cls.COMPLETED, cls.FAILED, cls.CANCELLED},
            cls.COMPLETED: set(),  # 终态
            cls.FAILED: {cls.DECOMPOSED, cls.CANCELLED},  # 可重试或取消
            cls.CANCELLED: set(),  # 终态
        }

class TransitionError(Exception):
    """状态转换错误"""
    pass

@dataclass
class StateTransition:
    """状态转换记录"""
    task_id: str
    from_state: TaskState
    to_state: TaskState
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str = ""
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }

# ============================================================================
# 任务数据结构
# ============================================================================

@dataclass
class Task:
    """工作流任务"""
    id: str
    title: str
    description: Optional[str] = None
    state: TaskState = TaskState.CREATED
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务 ID
    dependents: List[str] = field(default_factory=list)   # 被依赖的任务 ID
    assigned_agent: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def transition_to(self, new_state: TaskState, reason: str = "") -> StateTransition:
        """
        执行状态转换
        
        :param new_state: 目标状态
        :param reason: 转换原因
        :return: 转换记录
        :raises TransitionError: 非法状态转换
        """
        valid_transitions = TaskState.get_valid_transitions()
        
        if new_state not in valid_transitions[self.state]:
            raise TransitionError(
                f"非法状态转换：{self.state.value} → {new_state.value} "
                f"(任务 ID: {self.id}, 原因：{reason})"
            )
        
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now()
        
        if new_state == TaskState.RUNNING:
            self.started_at = datetime.now()
        elif new_state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            self.completed_at = datetime.now()
        
        return StateTransition(
            task_id=self.id,
            from_state=old_state,
            to_state=new_state,
            reason=reason,
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "assigned_agent": self.assigned_agent,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

# ============================================================================
# DAG 调度器
# ============================================================================

class DAGScheduler:
    """
    DAG 调度器
    
    功能：
    - 基于 finish-to-start 依赖构建 DAG
    - 拓扑排序确定执行顺序
    - 循环依赖检测
    - 并行任务识别
    """
    
    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)  # task_id -> dependencies
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)  # task_id -> dependents
    
    def add_task(self, task_id: str, dependencies: List[str] = None):
        """添加任务节点"""
        if task_id not in self.graph:
            self.graph[task_id] = set()
            self.reverse_graph[task_id] = set()
        
        if dependencies:
            for dep in dependencies:
                if dep not in self.graph:
                    self.graph[dep] = set()
                self.graph[task_id].add(dep)
                self.reverse_graph[dep].add(task_id)
    
    def detect_cycle(self) -> Optional[List[str]]:
        """
        检测循环依赖
        
        :return: 如果存在环，返回环上的任务 ID 列表；否则返回 None
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = defaultdict(int)
        parent: Dict[str, Optional[str]] = {}
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            color[node] = GRAY
            
            for neighbor in self.graph[node]:
                if color[neighbor] == GRAY:
                    # 发现后向边，存在环
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
                elif color[neighbor] == WHITE:
                    result = dfs(neighbor, path + [neighbor])
                    if result:
                        return result
            
            color[node] = BLACK
            return None
        
        for node in self.graph:
            if color[node] == WHITE:
                cycle = dfs(node, [node])
                if cycle:
                    return cycle
        
        return None
    
    def topological_sort(self) -> List[str]:
        """
        拓扑排序（Kahn 算法）
        
        :return: 任务 ID 的执行顺序列表
        :raises ValueError: 存在循环依赖时
        """
        cycle = self.detect_cycle()
        if cycle:
            raise ValueError(f"存在循环依赖：{' -> '.join(cycle)}")
        
        in_degree: Dict[str, int] = defaultdict(int)
        for task_id in self.graph:
            in_degree[task_id]  # 确保所有节点都在字典中
        
        for task_id, deps in self.graph.items():
            in_degree[task_id] = len(deps)
        
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            task_id = queue.popleft()
            result.append(task_id)
            
            for dependent in self.reverse_graph[task_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.graph):
            raise ValueError("拓扑排序失败，存在循环依赖")
        
        return result
    
    def get_ready_tasks(self, completed_tasks: Set[str], failed_tasks: Set[str]) -> List[str]:
        """
        获取可执行任务（所有依赖已完成）
        
        :param completed_tasks: 已完成的任务集合
        :param failed_tasks: 失败的任务集合
        :return: 可执行的任务 ID 列表
        """
        ready = []
        
        for task_id, dependencies in self.graph.items():
            # 跳过已完成或失败的任务
            if task_id in completed_tasks or task_id in failed_tasks:
                continue
            
            # 检查是否有依赖失败
            if dependencies & failed_tasks:
                # 依赖失败，标记为失败
                continue
            
            # 检查所有依赖是否完成
            if dependencies.issubset(completed_tasks):
                ready.append(task_id)
        
        return ready
    
    def get_parallel_groups(self) -> List[Set[str]]:
        """
        将任务分组为并行执行层
        
        :return: 每层包含可并行执行的任务集合
        """
        groups = []
        remaining = set(self.graph.keys())
        completed = set()
        
        while remaining:
            # 找到所有依赖已完成的任务
            layer = {
                task_id for task_id in remaining
                if self.graph[task_id].issubset(completed)
            }
            
            if not layer:
                raise ValueError("无法分组，可能存在循环依赖")
            
            groups.append(layer)
            completed.update(layer)
            remaining -= layer
        
        return groups

# ============================================================================
# 工作流引擎
# ============================================================================

class WorkflowEngine:
    """
    工作流引擎
    
    功能：
    - 任务生命周期管理
    - DAG 调度与执行
    - 并行任务控制
    - 上下文注入
    - 执行追踪
    """
    
    def __init__(self, max_concurrency: int = 4):
        """
        初始化工作流引擎
        
        :param max_concurrency: 最大并发任务数
        """
        self.max_concurrency = max_concurrency
        self.tasks: Dict[str, Task] = {}
        self.scheduler = DAGScheduler()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrency)
        
        # 状态变更监听器
        self._state_listeners: List[Callable[[StateTransition], None]] = []
        
        # 执行队列（用于并行控制）
        self._execution_queue: asyncio.Queue = None
        self._running_tasks: Set[str] = set()
        
        # 指标
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
    
    def register_listener(self, listener: Callable[[StateTransition], None]):
        """注册状态变更监听器"""
        self._state_listeners.append(listener)
    
    def _notify_state_change(self, transition: StateTransition):
        """通知状态变更"""
        for listener in self._state_listeners:
            try:
                listener(transition)
            except Exception as e:
                logger.error(f"State listener error: {e}")
    
    def create_task(self, task_id: str, title: str, 
                    description: Optional[str] = None,
                    dependencies: Optional[List[str]] = None,
                    assigned_agent: Optional[str] = None,
                    input_data: Optional[Dict[str, Any]] = None) -> Task:
        """
        创建任务
        
        :param task_id: 任务 ID
        :param title: 任务标题
        :param description: 任务描述
        :param dependencies: 依赖的任务 ID 列表
        :param assigned_agent: 分配的 Agent ID
        :param input_data: 输入数据
        :return: 创建的任务
        """
        if task_id in self.tasks:
            raise ValueError(f"任务已存在：{task_id}")
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            dependencies=dependencies or [],
            assigned_agent=assigned_agent,
            input_data=input_data or {},
        )
        
        self.tasks[task_id] = task
        self.scheduler.add_task(task_id, dependencies)
        self._total_tasks += 1
        
        logger.info(f"Task created: {task_id} (deps: {dependencies})")
        return task
    
    def decompose_task(self, task_id: str) -> StateTransition:
        """
        分解任务（CREATED → DECOMPOSED）
        
        :param task_id: 任务 ID
        :return: 状态转换记录
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在：{task_id}")
        
        task = self.tasks[task_id]
        transition = task.transition_to(TaskState.DECOMPOSED, "任务分解")
        self._notify_state_change(transition)
        
        logger.info(f"Task decomposed: {task_id}")
        return transition
    
    def _mark_dependencies_failed(self, failed_task_id: str):
        """标记依赖失败的任务为失败"""
        # 找到所有依赖此任务的任务
        to_fail = list(self.scheduler.reverse_graph.get(failed_task_id, []))
        
        for dep_id in to_fail:
            if self.tasks[dep_id].state == TaskState.WAITING:
                transition = self.tasks[dep_id].transition_to(
                    TaskState.FAILED,
                    f"依赖任务 {failed_task_id} 失败"
                )
                self._notify_state_change(transition)
                logger.warning(f"Task failed due to dependency failure: {dep_id}")
                self._mark_dependencies_failed(dep_id)
    
    async def run_task(self, task_id: str, executor_func: Callable) -> bool:
        """
        执行单个任务（由外部提供执行逻辑）
        
        :param task_id: 任务 ID
        :param executor_func: 任务执行函数（可以是同步或异步）
        :return: 是否成功
        """
        import inspect
        
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在：{task_id}")
        
        task = self.tasks[task_id]
        
        # 进入运行状态
        transition = task.transition_to(TaskState.RUNNING, "开始执行")
        self._notify_state_change(transition)
        
        self._running_tasks.add(task_id)
        
        try:
            # 判断是协程函数还是普通函数
            if inspect.iscoroutinefunction(executor_func):
                # 异步函数
                result = await executor_func(task)
            else:
                # 同步函数
                result = await asyncio.get_event_loop().run_in_executor(
                    self.executor, executor_func, task
                )
            
            task.output_data = result if isinstance(result, dict) else {"result": result}
            
            # 完成
            transition = task.transition_to(TaskState.COMPLETED, "执行成功")
            self._notify_state_change(transition)
            self._completed_tasks += 1
            logger.info(f"Task completed: {task_id}")
            return True
            
        except Exception as e:
            task.error_message = str(e)
            transition = task.transition_to(TaskState.FAILED, f"执行失败：{e}")
            self._notify_state_change(transition)
            self._failed_tasks += 1
            self._mark_dependencies_failed(task_id)
            logger.error(f"Task failed: {task_id}, error: {e}")
            return False
        
        finally:
            self._running_tasks.discard(task_id)
    
    async def execute_workflow(self, task_executors: Dict[str, Callable]) -> Dict[str, Any]:
        """
        执行整个工作流
        
        :param task_executors: 任务 ID -> 执行函数的映射
        :return: 执行结果
        """
        # 检测循环依赖
        cycle = self.scheduler.detect_cycle()
        if cycle:
            raise ValueError(f"工作流存在循环依赖：{' -> '.join(cycle)}")
        
        # 获取并行执行组
        parallel_groups = self.scheduler.get_parallel_groups()
        
        all_results = {}
        
        for group_id, group in enumerate(parallel_groups):
            logger.info(f"Executing parallel group {group_id + 1}: {group}")
            
            # 限制并发数
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            async def limited_execute(task_id: str):
                async with semaphore:
                    if task_id in task_executors:
                        success = await self.run_task(task_id, task_executors[task_id])
                        all_results[task_id] = {"success": success, "result": self.tasks[task_id].output_data}
                    else:
                        logger.warning(f"No executor found for task: {task_id}")
                        all_results[task_id] = {"success": False, "error": "No executor"}
            
            # 并行执行当前组的所有任务
            await asyncio.gather(*[limited_execute(task_id) for task_id in group])
        
        # 汇总结果
        return {
            "total_tasks": self._total_tasks,
            "completed_tasks": self._completed_tasks,
            "failed_tasks": self._failed_tasks,
            "results": all_results,
            "success": self._failed_tasks == 0,
        }
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_state(self, state: TaskState) -> List[Task]:
        """获取指定状态的任务"""
        return [t for t in self.tasks.values() if t.state == state]
    
    def get_metrics(self) -> dict:
        """获取引擎指标"""
        return {
            "total_tasks": self._total_tasks,
            "completed_tasks": self._completed_tasks,
            "failed_tasks": self._failed_tasks,
            "running_tasks": len(self._running_tasks),
            "max_concurrency": self.max_concurrency,
        }
    
    def shutdown(self):
        """关闭引擎"""
        self.executor.shutdown(wait=True)
        logger.info("Workflow engine shutdown")
