"""
Nexus Reins 仓库模块 - 争议仓库

提供 Dispute 实体的数据持久化接口
"""

from typing import Optional, List
from models import Dispute, DisputeType, DisputeStatus
from persistence.tables import disputes

class DisputeRepository:
    """争议仓库"""
    
    def __init__(self, engine):
        self._engine = engine
    
    def _to_entity(self, row) -> Dispute:
        return Dispute(
            id=row.id,
            dispute_type=DisputeType(row.dispute_type) if row.dispute_type else None,
            description=row.description,
            involved_agents=row.involved_agents or [],
            related_task_id=row.related_task_id,
            status=DisputeStatus(row.status),
            resolution=row.resolution,
            resolved_by=row.resolved_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            resolved_at=row.resolved_at,
        )
    
    def _to_row(self, entity: Dispute) -> dict:
        return {
            "id": entity.id,
            "dispute_type": entity.dispute_type.value if entity.dispute_type else None,
            "description": entity.description,
            "involved_agents": entity.involved_agents,
            "related_task_id": entity.related_task_id,
            "status": entity.status.value,
            "resolution": entity.resolution,
            "resolved_by": entity.resolved_by,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "resolved_at": entity.resolved_at,
        }
    
    def save(self, entity: Dispute) -> Dispute:
        with self._engine.begin() as conn:
            if entity.id:
                conn.execute(
                    disputes.update()
                    .where(disputes.c.id == entity.id)
                    .values(**self._to_row(entity))
                )
            else:
                conn.execute(disputes.insert().values(**self._to_row(entity)))
            return entity
    
    def get(self, entity_id: str) -> Optional[Dispute]:
        with self._engine.connect() as conn:
            row = conn.execute(disputes.select().where(disputes.c.id == entity_id)).first()
            return self._to_entity(row) if row else None
    
    def list(self, status: DisputeStatus = None) -> List[Dispute]:
        with self._engine.connect() as conn:
            if status:
                row_set = conn.execute(disputes.select().where(disputes.c.status == status.value)).fetchall()
            else:
                row_set = conn.execute(disputes.select()).fetchall()
            return [self._to_entity(row) for row in row_set]
    
    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(disputes.delete().where(disputes.c.id == entity_id))
            return result.rowcount > 0