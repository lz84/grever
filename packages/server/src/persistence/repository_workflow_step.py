"""
Nexus Reins 仓库模块 - 工作流步骤仓库

提供 SqlWorkflowStep 实体的数据持久化接口
"""

from typing import Optional, List
from models import SqlWorkflowStep, WorkflowStepStatus
from persistence.tables import workflow_steps

class WorkflowStepRepository:
    """工作流步骤仓库"""

    def __init__(self, engine):
        self._engine = engine

    def _to_entity(self, row) -> SqlWorkflowStep:
        return SqlWorkflowStep(
            id=row.id,
            workflow_id=row.workflow_id,
            name=row.name,
            description=row.description,
            status=row.status,
            dependencies=row.dependencies or [],
            order=row.order,
            agent_id=row.agent_id,
            input_data=row.input_data or {},
            output_data=row.output_data or {},
            error=row.error,
            retry_count=row.retry_count,
            max_retries=row.max_retries,
            timeout_seconds=row.timeout_seconds,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    def _to_row(self, entity: SqlWorkflowStep) -> dict:
        return {
            "id": entity.id,
            "workflow_id": entity.workflow_id,
            "name": entity.name,
            "description": entity.description,
            "status": entity.status,
            "dependencies": entity.dependencies,
            "order": entity.order,
            "agent_id": entity.agent_id,
            "input_data": entity.input_data,
            "output_data": entity.output_data,
            "error": entity.error,
            "retry_count": entity.retry_count,
            "max_retries": entity.max_retries,
            "timeout_seconds": entity.timeout_seconds,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "started_at": entity.started_at,
            "completed_at": entity.completed_at,
        }

    def save(self, entity: SqlWorkflowStep) -> SqlWorkflowStep:
        with self._engine.begin() as conn:
            if entity.id:
                conn.execute(
                    workflow_steps.update()
                    .where(workflow_steps.c.id == entity.id)
                    .values(**self._to_row(entity))
                )
            else:
                conn.execute(workflow_steps.insert().values(**self._to_row(entity)))
            return entity

    def get(self, entity_id: str) -> Optional[SqlWorkflowStep]:
        with self._engine.connect() as conn:
            row = conn.execute(workflow_steps.select().where(workflow_steps.c.id == entity_id)).first()
            return self._to_entity(row) if row else None

    def list_by_workflow(self, workflow_id: str) -> List[SqlWorkflowStep]:
        with self._engine.connect() as conn:
            row_set = conn.execute(
                workflow_steps.select()
                .where(workflow_steps.c.workflow_id == workflow_id)
                .order_by(workflow_steps.c.order)
            ).fetchall()
            return [self._to_entity(row) for row in row_set]

    def list(self, status: str = None, agent_id: str = None) -> List[SqlWorkflowStep]:
        with self._engine.connect() as conn:
            query = workflow_steps.select()
            if status:
                query = query.where(workflow_steps.c.status == status)
            if agent_id:
                query = query.where(workflow_steps.c.agent_id == agent_id)
            row_set = conn.execute(query.order_by(workflow_steps.c.order)).fetchall()
            return [self._to_entity(row) for row in row_set]

    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(workflow_steps.delete().where(workflow_steps.c.id == entity_id))
            return result.rowcount > 0

    def delete_by_workflow(self, workflow_id: str) -> int:
        """删除工作流的所有步骤"""
        with self._engine.begin() as conn:
            result = conn.execute(
                workflow_steps.delete().where(workflow_steps.c.workflow_id == workflow_id)
            )
            return result.rowcount

    def get_runnable_steps(self, workflow_id: str, completed_step_ids: List[str]) -> List[SqlWorkflowStep]:
        """获取可执行的步骤（所有依赖已完成的步骤）"""
        with self._engine.connect() as conn:
            all_steps = conn.execute(
                workflow_steps.select().where(workflow_steps.c.workflow_id == workflow_id)
            ).fetchall()

            runnable = []
            for row in all_steps:
                if row.status != WorkflowStepStatus.PENDING:
                    continue
                deps = row.dependencies or []
                if all(dep in completed_step_ids for dep in deps):
                    runnable.append(self._to_entity(row))
            return runnable