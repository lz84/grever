"""
Grever Reins 仓库模块 - Agent 仓库

提供 AgentInfo 实体的数据持久化接口
"""

from typing import Optional, List
from models import AgentInfo, AgentStatus
from persistence.tables import agents

class AgentRepository:
    """Agent 仓库"""
    
    def __init__(self, engine):
        self._engine = engine
    
    def _to_entity(self, row) -> AgentInfo:
        return AgentInfo(
            id=row.id,
            name=row.name,
            capabilities=row.capabilities or [],
            status=AgentStatus(row.status),
            address=row.address,
            metadata=row.metadata or {},
            load=row.load,
            current_load=row.load,
            current_tasks=row.current_tasks,
            model_name=getattr(row, 'model_name', '') or '',
            registered_at=row.registered_at,
            last_heartbeat=row.last_heartbeat,
        )
    
    def _to_row(self, entity: AgentInfo) -> dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "capabilities": entity.capabilities,
            "status": entity.status.value,
            "address": entity.address,
            "metadata": entity.metadata,
            "load": entity.load,
            "current_tasks": entity.current_tasks,
            "model_name": entity.model_name,
            "registered_at": entity.registered_at,
            "last_heartbeat": entity.last_heartbeat,
        }
    
    def save(self, entity: AgentInfo) -> AgentInfo:
        with self._engine.begin() as conn:
            existing = conn.execute(agents.select().where(agents.c.id == entity.id)).first()
            if existing:
                conn.execute(
                    agents.update()
                    .where(agents.c.id == entity.id)
                    .values(**self._to_row(entity))
                )
            else:
                conn.execute(agents.insert().values(**self._to_row(entity)))
            return entity
    
    def get(self, entity_id: str) -> Optional[AgentInfo]:
        with self._engine.connect() as conn:
            row = conn.execute(agents.select().where(agents.c.id == entity_id)).first()
            return self._to_entity(row) if row else None
    
    def list(self, status: AgentStatus = None) -> List[AgentInfo]:
        with self._engine.connect() as conn:
            if status:
                row_set = conn.execute(agents.select().where(agents.c.status == status.value)).fetchall()
            else:
                row_set = conn.execute(agents.select()).fetchall()
            return [self._to_entity(row) for row in row_set]
    
    def delete(self, entity_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(agents.delete().where(agents.c.id == entity_id))
            return result.rowcount > 0