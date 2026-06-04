"""
Nexus Reins 仓库模块 - 任务仓库

提供 Task 实体的数据持久化接口
"""

from typing import Optional, List
from models import Task, TaskStatus, Priority
from persistence.tables import tasks

class TaskRepository:
    """任务仓库"""
    
    def __init__(self, engine):
        self._engine = engine
    
    def _to_entity(self, row) -> Task:
        # Priority: 支持 string 和 int 两种格式（迁移兼容）
        raw_priority = row.priority
        if isinstance(raw_priority, str):
            priority_map = {'critical': Priority.P0, 'high': Priority.P1, 'medium': Priority.P2, 'low': Priority.P3}
            priority_val = priority_map.get(raw_priority.lower(), Priority.P2)
        else:
            priority_val = Priority(raw_priority) if raw_priority in (0, 1, 2, 3) else Priority.P2
        return Task(
            id=row.id,
            title=row.title,
            description=row.description,
            project_id=row.project_id,
            goal_id=row.goal_id,
            assigned_agent=row.assigned_agent,
            status=str(row.status) if row.status else 'todo',
            priority=priority_val,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            result=row.result,
        )
    
    def _to_row(self, entity: Task) -> dict:
        # Priority int → string for DB storage
        priority_str_map = {0: 'critical', 1: 'high', 2: 'medium', 3: 'low'}
        priority_val = entity.priority
        if isinstance(priority_val, int):
            priority_str = priority_str_map.get(priority_val, 'medium')
        else:
            priority_str = priority_val.value if hasattr(priority_val, 'value') else str(priority_val)
            if priority_str in ('0', '1', '2', '3'):
                priority_str = priority_str_map.get(int(priority_str), 'medium')
        return {
            "id": entity.id,
            "title": entity.title,
            "description": entity.description,
            "project_id": entity.project_id,
            "goal_id": entity.goal_id,
            "assigned_agent": entity.assigned_agent,
            "status": entity.status.value if hasattr(entity.status, 'value') else str(entity.status),
            "priority": priority_str,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "started_at": entity.started_at,
            "completed_at": entity.completed_at,
            "result": entity.result,
        }

    def save(self, entity: Task) -> Task:
        with self._engine.begin() as conn:
            if entity.id:
                conn.execute(
                    tasks.update()
                    .where(tasks.c.id == entity.id)
                    .values(**self._to_row(entity))
                )
            else:
                conn.execute(tasks.insert().values(**self._to_row(entity)))
            return entity
    
    def get(self, entity_id: str) -> Optional[Task]:
        with self._engine.connect() as conn:
            row = conn.execute(tasks.select().where(tasks.c.id == entity_id)).first()
            return self._to_entity(row) if row else None
    
    def list(
        self,
        status: TaskStatus = None,
        project_id: str = None,
        assigned_agent: str = None,
    ) -> List[Task]:
        with self._engine.connect() as conn:
            query = tasks.select()
            if status:
                query = query.where(tasks.c.status == status.value)
            if project_id:
                query = query.where(tasks.c.project_id == project_id)
            if assigned_agent:
                query = query.where(tasks.c.assigned_agent == assigned_agent)
            row_set = conn.execute(query).fetchall()
            tasks_list = [self._to_entity(row) for row in row_set]
            return sorted(tasks_list, key=lambda t: (t.priority.value, t.created_at))
    
    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(tasks.delete().where(tasks.c.id == entity_id))
            return result.rowcount > 0