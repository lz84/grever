"""Workflow 业务逻辑核心类"""

from loguru import logger
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import json

from persistence.database import DatabaseManager
from persistence.repository import WorkflowRepository, WorkflowStepRepository
from persistence.tables import workflows, workflow_steps, tasks
from models import WorkflowStatus, WorkflowStepStatus, TaskStatus
from reins.core.assignment import get_agent_registry, get_task_assigner
from reins.common.event_bus import WorkflowEvent, get_event_bus
from shared.eventbus.manager import get_event_bus_manager

class WorkflowsLogic:
    """Workflow 业务逻辑"""

    def __init__(self, db_manager: DatabaseManager):
        self._db_manager = db_manager

    def _get_repositories(self):
        """获取仓库会话"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self._db_manager.engine)
        session = Session()
        return session, WorkflowRepository(self._db_manager.engine), WorkflowStepRepository(self._db_manager.engine)

    def _emit_workflow_event(self, event_type: str, workflow_id: str, data: Dict[str, Any] = None):
        """发布 Workflow 事件到 EventBus"""
        try:
            bus = get_event_bus_manager().get_adapter(None)
            if bus:
                bus.publish(WorkflowEvent(event_type=event_type, workflow_id=workflow_id, step_id="", data=data or {}))
        except Exception as e:
            logger.error(f"[Workflow Event] Publish error: {e}")

    def _extract_step_capabilities(self, step) -> List[str]:
        """提取步骤的能力需求"""
        capabilities = []
        input_data = getattr(step, 'input_data', {}) or {}
        if isinstance(input_data, dict):
            caps = input_data.get('capabilities', [])
            if isinstance(caps, list):
                capabilities.extend(caps)
            elif isinstance(caps, str):
                capabilities.append(caps)

        name = getattr(step, 'name', '') or ''
        desc = getattr(step, 'description', '') or ''

        capability_keywords = {
            'rescue': ['rescue', '搜救', '救援', '被困人员', '营救', '搜索'],
            'medical': ['medical', '医疗', '救治', '伤员', '急救'],
            'fire': ['fire', '消防', '灭火', '火灾', '燃烧'],
            'chemical': ['chemical', '化工', '化工厂', '危化品', '泄漏', '有毒'],
            'communication': ['communication', '通讯', '通信', '联络', '信号'],
            'transport': ['transport', '运输', '转运', '运送', '物流'],
            'assessment': ['assessment', '评估', '分析', '判断', '勘测'],
            'command': ['command', '指挥', '协调', '调度', '统筹'],
            'logistics': ['logistics', '后勤', '物资', '保障', '供给'],
            'search': ['search', '搜索', '探测', '寻找', '定位'],
        }

        text = f"{name} {desc}".lower()
        for cap, keywords in capability_keywords.items():
            if any(kw in text for kw in keywords):
                capabilities.append(cap)

        return list(set(capabilities))

    def _map_step_to_task_priority(self, step) -> int:
        """将步骤映射到任务优先级"""
        order = getattr(step, 'order', 0) or 0
        if order <= 1:
            return 1
        elif order <= 3:
            return 2
        else:
            return 3

    def activate_workflow(self, workflow_id: str):
        """MA-K233-1: Workflow 激活"""
        from sqlalchemy import text
        from fastapi import HTTPException
        session, workflow_repo, step_repo = self._get_repositories()
        try:
            workflow = workflow_repo.get(workflow_id)
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
            if workflow.status == WorkflowStatus.RUNNING:
                raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} is already running")
            if workflow.status == WorkflowStatus.COMPLETED:
                raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} is already completed")
            steps = step_repo.list_by_workflow(workflow_id)
            if not steps:
                raise HTTPException(status_code=400, detail=f"No steps found for workflow: {workflow_id}")
            task_ids = []
            with self._db_manager.engine.begin() as conn:
                for step in steps:
                    task_id = str(uuid.uuid4())
                    conn.execute(tasks.insert().values(
                        id=task_id, title=step.name, description=step.description or "",
                        goal_id=workflow.goal_id, project_id=None, assigned_agent=step.agent_id,
                        status="pending", priority=self._map_step_to_task_priority(step),
                        dependencies=step.dependencies or [], depends_on=[],
                        created_at=datetime.now(), updated_at=datetime.now(),
                        started_at=None, completed_at=None,
                        estimated_hours=step.timeout_seconds, actual_hours=None, result=None,
                    ))
                    task_ids.append(task_id)
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now()
            workflow_repo.save(workflow)
            self._emit_workflow_event("workflow_started", workflow_id, {"step_count": len(steps), "task_count": len(task_ids)})
            from reins.api.workflows import ActivateWorkflowResponse
            return ActivateWorkflowResponse(workflow_id=workflow_id, tasks_created=len(task_ids), task_ids=task_ids, status=workflow.status)
        finally:
            session.close()

    def register_event_listeners(self):
        """MA-K233-2: Register Workflow event listeners"""
        try:
            bus = get_event_bus_manager().get_adapter(None)
            if bus:
                try:
                    bus.subscribe("task_completed", self._on_task_completed)
                except Exception as e:
                    logger.error(f"[MA-K233-2] subscribe task_completed error: {e}")
                try:
                    bus.subscribe("task_failed", self._on_task_failed)
                except Exception as e:
                    logger.error(f"[MA-K233-2] subscribe task_failed error: {e}")
        except Exception as e:
            logger.error(f"[MA-K233-2] Event listener registration error: {e}")

    def _on_task_completed(self, event: WorkflowEvent):
        """处理 task_completed 事件"""
        from sqlalchemy import text
        task_id = event.data.get("task_id")
        workflow_id = event.data.get("workflow_id")
        if not workflow_id and self._db_manager:
            with self._db_manager.engine.connect() as conn:
                r = conn.execute(text("SELECT id FROM workflows WHERE id = (SELECT workflow_id FROM workflow_steps WHERE id = :task_id)"), {"task_id": task_id}).fetchone()
                if r:
                    workflow_id = r.id
        if not workflow_id:
            return
        if not self._db_manager:
            return
        session, workflow_repo, step_repo = self._get_repositories()
        try:
            workflow = workflow_repo.get(workflow_id)
            if not workflow:
                return
            step = step_repo.get(task_id)
            if not step:
                with self._db_manager.engine.connect() as conn:
                    r = conn.execute(text("SELECT workflow_id FROM workflow_steps WHERE id = :step_id"), {"step_id": task_id}).fetchone()
                    if r:
                        step = step_repo.get(task_id)
            if step:
                step.status = WorkflowStepStatus.DONE
                step.completed_at = datetime.now()
                step_repo.save(step)
            all_steps = step_repo.list_by_workflow(workflow_id)
            all_done = all(s.status == WorkflowStepStatus.DONE for s in all_steps)
            any_blocked = any(s.status == WorkflowStepStatus.BLOCKED for s in all_steps)
            if all_done:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                self._emit_workflow_event("workflow_completed", workflow_id, {"completed_steps": len(all_steps)})
            elif any_blocked:
                workflow.status = WorkflowStatus.BLOCKED
                self._emit_workflow_event("workflow_blocked", workflow_id, {"blocked_steps": [s.id for s in all_steps if s.status == WorkflowStepStatus.BLOCKED]})
            workflow_repo.save(workflow)
        except Exception as e:
            logger.error(f"[MA-K233-2] Task completed handler error: {e}")
        finally:
            session.close()

    def _on_task_failed(self, event: WorkflowEvent):
        """处理 task_failed 事件"""
        task_id = event.data.get("task_id")
        error = event.data.get("error", "")
        workflow_id = event.data.get("workflow_id")
        if not workflow_id:
            return
        if not self._db_manager:
            return
        session, workflow_repo, step_repo = self._get_repositories()
        try:
            workflow = workflow_repo.get(workflow_id)
            if not workflow:
                return
            step = step_repo.get(task_id)
            if step:
                if getattr(step, 'retry_count', 0) < getattr(step, 'max_retries', 3):
                    step.status = WorkflowStepStatus.PENDING
                    step.retry_count = getattr(step, 'retry_count', 0) + 1
                    step.error = error
                else:
                    step.status = WorkflowStepStatus.BLOCKED
                    step.error = f"Failed after {getattr(step, 'retry_count', 0)} retries: {error}"
                step.updated_at = datetime.now()
                step_repo.save(step)
            all_steps = step_repo.list_by_workflow(workflow_id)
            all_done = all(s.status == WorkflowStepStatus.DONE for s in all_steps)
            any_blocked = any(s.status == WorkflowStepStatus.BLOCKED for s in all_steps)
            if all_done:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
            elif any_blocked:
                workflow.status = WorkflowStatus.BLOCKED
            workflow_repo.save(workflow)
        except Exception as e:
            logger.error(f"[MA-K233-2] Task failed handler error: {e}")
        finally:
            session.close()

    def get_workflow_progress(self, workflow_id: str):
        """MA-K233-3: 获取工作流进度"""
        from fastapi import HTTPException
        if not self._db_manager:
            raise RuntimeError("Database manager not initialized")
        session, workflow_repo, step_repo = self._get_repositories()
        try:
            workflow = workflow_repo.get(workflow_id)
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
            steps = step_repo.list_by_workflow(workflow_id)
            completed_steps = sum(1 for s in steps if s.status == WorkflowStepStatus.DONE)
            progress_percent = (completed_steps / len(steps) * 100) if steps else 0.0
            current_step = next((s.id for s in steps if s.status in (WorkflowStepStatus.RUNNING, WorkflowStepStatus.PENDING)), None)
            steps_info = [{"step_id": s.id, "name": s.name, "status": s.status, "agent_id": s.agent_id, "order": s.order, "error": s.error} for s in steps]
            from reins.api.workflows import WorkflowProgressResponse
            return WorkflowProgressResponse(workflow_id=workflow_id, completed_steps=completed_steps, total_steps=len(steps), progress_percent=round(progress_percent, 2), current_step=current_step, status=workflow.status, steps=steps_info)
        finally:
            session.close()
