"""
Nexus Reins 仓库模块 - 工作流仓库

提供 SqlWorkflow 实体的数据持久化接口
"""

import json
from typing import Optional, List
from models import SqlWorkflow, WorkflowStatus
from persistence.tables import workflows

class WorkflowRepository:
    """工作流仓库"""

    def __init__(self, engine):
        self._engine = engine

    def _to_entity(self, row) -> SqlWorkflow:
        def _parse_json(val):
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                return val
            try:
                return json.loads(val)
            except (ValueError, TypeError):
                return None
        return SqlWorkflow(
            id=row.id,
            goal_id=row.goal_id,
            status=row.status,
            name=row.name,
            description=row.description,
            dag=_parse_json(row.dag),
            workflow_metadata=_parse_json(row.workflow_metadata),
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    def _to_row(self, entity: SqlWorkflow) -> dict:
        return {
            "id": entity.id,
            "goal_id": entity.goal_id,
            "status": entity.status,
            "name": entity.name,
            "description": entity.description,
            "dag": entity.dag,
            "workflow_metadata": entity.workflow_metadata,
            "created_by": entity.created_by,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "started_at": entity.started_at,
            "completed_at": entity.completed_at,
        }

    def save(self, entity: SqlWorkflow) -> SqlWorkflow:
        with self._engine.begin() as conn:
            if entity.id:
                conn.execute(
                    workflows.update()
                    .where(workflows.c.id == entity.id)
                    .values(**self._to_row(entity))
                )
            else:
                conn.execute(workflows.insert().values(**self._to_row(entity)))
            return entity

    def get(self, entity_id: str) -> Optional[SqlWorkflow]:
        with self._engine.connect() as conn:
            row = conn.execute(workflows.select().where(workflows.c.id == entity_id)).first()
            return self._to_entity(row) if row else None

    def list(self, status: str = None, goal_id: str = None) -> List[SqlWorkflow]:
        with self._engine.connect() as conn:
            query = workflows.select()
            if status:
                query = query.where(workflows.c.status == status)
            if goal_id:
                query = query.where(workflows.c.goal_id == goal_id)
            row_set = conn.execute(query.order_by(workflows.c.created_at.desc())).fetchall()
            return [self._to_entity(row) for row in row_set]

    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(workflows.delete().where(workflows.c.id == entity_id))
            return result.rowcount > 0

    def get_with_steps(self, entity_id: str) -> Optional[SqlWorkflow]:
        """获取工作流及其所有步骤"""
        from persistence.repository_workflow_step import WorkflowStepRepository
        workflow = self.get(entity_id)
        if not workflow:
            return None
        step_repo = WorkflowStepRepository(self._engine)
        workflow.steps = step_repo.list_by_workflow(entity_id)
        return workflow