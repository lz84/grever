"""
Grever Reins 仓库模块 - 项目仓库

提供 Project 实体的数据持久化接口
"""

from typing import Optional, List
from models import Project, ProjectStatus
from persistence.tables import projects

class ProjectRepository:
    """项目仓库"""
    
    def __init__(self, engine):
        self._engine = engine
    
    def _to_entity(self, row) -> Project:
        return Project(
            id=row.id,
            name=row.name,
            description=row.description,
            goal_id=row.goal_id,
            status=ProjectStatus(row.status),
            members=row.members or [],
            task_ids=row.task_ids or [],
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at,
        )
    
    def _to_row(self, entity: Project) -> dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "description": entity.description,
            "goal_id": entity.goal_id,
            "status": entity.status.value,
            "members": entity.members,
            "task_ids": entity.task_ids,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "completed_at": entity.completed_at,
        }
    
    def save(self, entity: Project) -> Project:
        with self._engine.begin() as conn:
            if entity.id:
                conn.execute(
                    projects.update()
                    .where(projects.c.id == entity.id)
                    .values(**self._to_row(entity))
                )
            else:
                conn.execute(projects.insert().values(**self._to_row(entity)))
            return entity
    
    def get(self, entity_id: str) -> Optional[Project]:
        with self._engine.connect() as conn:
            row = conn.execute(projects.select().where(projects.c.id == entity_id)).first()
            return self._to_entity(row) if row else None
    
    def list(self, status: ProjectStatus = None) -> List[Project]:
        with self._engine.connect() as conn:
            if status:
                row_set = conn.execute(projects.select().where(projects.c.status == status.value)).fetchall()
            else:
                row_set = conn.execute(projects.select()).fetchall()
            return [self._to_entity(row) for row in row_set]
    
    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(projects.delete().where(projects.c.id == entity_id))
            return result.rowcount > 0