"""
Nexus Reins 仓库模块 - 目标仓库

提供 Goal 实体的数据持久化接口
"""

from typing import Optional, List
from models import Goal, GoalStatus
from persistence.tables import goals

class GoalRepository:
    """目标仓库"""
    
    def __init__(self, engine):
        self._engine = engine
    
    def _to_entity(self, row) -> Goal:
        """数据库行转实体"""
        return Goal(
            id=row.id,
            title=row.title,
            description=row.description,
            parent_id=row.parent_id,
            status=GoalStatus(row.status),
            progress=row.progress,
            task_ids=row.task_ids or [],
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at,
        )
    
    def _to_row(self, entity: Goal) -> dict:
        """实体转数据库行"""
        return {
            "id": entity.id,
            "title": entity.title,
            "description": entity.description,
            "parent_id": entity.parent_id,
            "status": entity.status.value,
            "progress": entity.progress,
            "task_ids": entity.task_ids,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "completed_at": entity.completed_at,
        }
    
    def save(self, entity: Goal) -> Goal:
        with self._engine.begin() as conn:
            if entity.id:
                existing = conn.execute(
                    goals.select().where(goals.c.id == entity.id)
                ).first()
                if existing:
                    conn.execute(
                        goals.update()
                        .where(goals.c.id == entity.id)
                        .values(**self._to_row(entity))
                    )
                else:
                    conn.execute(goals.insert().values(**self._to_row(entity)))
            else:
                conn.execute(goals.insert().values(**self._to_row(entity)))
            return entity
    
    def get(self, entity_id: str) -> Optional[Goal]:
        with self._engine.connect() as conn:
            row = conn.execute(goals.select().where(goals.c.id == entity_id)).first()
            return self._to_entity(row) if row else None
    
    def list(self, status: GoalStatus = None) -> List[Goal]:
        with self._engine.connect() as conn:
            if status:
                row_set = conn.execute(goals.select().where(goals.c.status == status.value)).fetchall()
            else:
                row_set = conn.execute(goals.select()).fetchall()
            return [self._to_entity(row) for row in row_set]
    
    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(goals.delete().where(goals.c.id == entity_id))
            return result.rowcount > 0