"""
Event 持久化存储（P5-01-06）

EventStore 负责：
- 将 Event 写入 SQLite 数据库
- 按 agent_id + 时间戳分页查询
- 支持 last_event_id 增量拉取模式
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from reins.common.database import DB_PATH

from sqlalchemy import (
    create_engine,
    func,
)
from sqlalchemy.engine import Engine

from shared.eventbus.types import Event, EventPayload
from shared.eventbus.models import make_events_table, metadata

logger = logging.getLogger(__name__)


class EventStore:
    """
    Event 持久化存储（P5-01-06）

    使用 SQLite 数据库，支持：
    - 写入 Event
    - 按 agent_id + 时间范围查询
    - last_event_id 增量拉取
    - 分页查询
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._engine: Optional[Engine] = None
        self._table = None

    @property
    def engine(self) -> Engine:
        """获取或创建数据库引擎"""
        if self._engine is None:
            db_url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                pool_pre_ping=True,
            )
        return self._engine

    def ensure_table(self) -> None:
        """确保 events 表已创建"""
        if self._table is None:
            # 如果 metadata 中已有 events 表，复用它
            if "events" in metadata.tables:
                self._table = metadata.tables["events"]
            else:
                self._table = make_events_table(metadata)
                metadata.create_all(self.engine, tables=[self._table])
            logger.info(f"[EventStore] events table ensured at {self.db_path}")

    def save(self, event: Event) -> str:
        """
        保存 Event 到数据库（P5-01-06）

        Returns:
            event_id: 保存的事件 ID
        """
        self.ensure_table()

        payload = event.payload.to_dict() if isinstance(event.payload, EventPayload) else event.payload

        with self.engine.begin() as conn:
            conn.execute(
                self._table.insert().values(
                    event_id=event.event_id,
                    agent_id=event.agent_id,
                    event_type=event.event_type,
                    payload=json.dumps(payload, ensure_ascii=False),
                    created_at=event.created_at.isoformat() if event.created_at else datetime.now().isoformat(),
                    read_at=event.read_at.isoformat() if event.read_at else None,
                    workflow_id=event.payload.workflow_id if event.payload else None,
                ),
            )

        logger.debug(f"[EventStore] Saved event {event.event_id} of type {event.event_type}")
        return event.event_id

    def get_by_id(self, event_id: str) -> Optional[Event]:
        """根据 ID 获取 Event"""
        self.ensure_table()

        with self.engine.begin() as conn:
            row = conn.execute(
                self._table.select().where(self._table.c.event_id == event_id),
            ).fetchone()

        if not row:
            return None

        return self._row_to_event(dict(row))

    def get_pending(
        self,
        agent_id: str,
        since: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        获取 Agent 的待处理事件（P5-01-06，P5-01-04）

        - agent_id: Agent ID
        - since: 上次获取的时间戳（ISO 格式），None 表示从头
        - event_types: 事件类型过滤
        - limit: 最大返回数量

        Returns:
            未读事件列表（按 created_at 升序）
        """
        self.ensure_table()

        conditions = [self._table.c.agent_id == agent_id]

        if since:
            conditions.append(self._table.c.created_at > since)

        if event_types:
            conditions.append(self._table.c.event_type.in_(event_types))

        stmt = (
            self._table.select()
            .where(*conditions)
            .order_by(self._table.c.created_at.asc())
            .limit(limit)
        )

        with self.engine.begin() as conn:
            rows = conn.execute(stmt).fetchall()

        events = []
        for row in rows:
            event = self._row_to_event(dict(row))
            if event:
                events.append(event)

        logger.debug(f"[EventStore] get_pending for agent={agent_id}, since={since}, got={len(events)}")
        return events

    def mark_read(self, event_ids: List[str]) -> int:
        """
        标记事件为已读（P5-01-04）

        Returns:
            实际标记的事件数量
        """
        if not event_ids:
            return 0

        self.ensure_table()
        now = datetime.now().isoformat()

        with self.engine.begin() as conn:
            result = conn.execute(
                self._table.update()
                .where(self._table.c.event_id.in_(event_ids))
                .where(self._table.c.read_at.is_(None))
                .values(read_at=now),
            )

        logger.debug(f"[EventStore] Marked {result.rowcount} events as read")
        return result.rowcount

    def get_total_count(
        self,
        agent_id: str,
        event_types: Optional[List[str]] = None,
    ) -> int:
        """获取 Agent 的事件总数"""
        self.ensure_table()

        conditions = [self._table.c.agent_id == agent_id]

        if event_types:
            conditions.append(self._table.c.event_type.in_(event_types))

        stmt = self._table.select().with_only_columns([func.count()]).where(*conditions)

        with self.engine.begin() as conn:
            row = conn.execute(stmt).fetchone()

        return row[0] if row else 0

    def _row_to_event(self, row: dict) -> Optional[Event]:
        """将数据库行转换为 Event 对象"""
        try:
            payload_data = row.get("payload", {})
            if isinstance(payload_data, str):
                payload_data = json.loads(payload_data)

            created_at = row.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            read_at = row.get("read_at")
            if isinstance(read_at, str):
                read_at = datetime.fromisoformat(read_at)

            payload = EventPayload(**payload_data) if payload_data else EventPayload()

            return Event(
                event_id=row.get("event_id", str(uuid.uuid4())),
                agent_id=row.get("agent_id"),
                event_type=row.get("event_type", ""),
                payload=payload,
                created_at=created_at,
                read_at=read_at,
            )
        except Exception as e:
            logger.warning(f"[EventStore] Failed to parse event row: {e}")
            return None
