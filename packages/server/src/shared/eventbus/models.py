"""
EventBus 数据库模型（P5-01-06）

新增 events 表用于 Event 持久化。
使用 SQLAlchemy Core，支持多数据库后端。
"""

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Integer,
    DateTime,
    JSON,
    Index,
    text,
)
from datetime import datetime
import uuid


metadata = MetaData()


# ========== 事件表 (events) ==========
def make_events_table(metadata: MetaData) -> Table:
    """
    创建 events 表（P5-01-06）

    字段：
    - event_id: 主键 UUID
    - agent_id: 关联 Agent ID（可为空，用于路由）
    - event_type: 事件类型
    - payload: JSON 格式的负载
    - created_at: 创建时间
    - read_at: 已读时间（轮询去重）
    - workflow_id: 关联工作流 ID（可为空）
    """
    return Table(
        "events",
        metadata,
        Column(
            "event_id",
            String(36),
            primary_key=True,
            default=lambda: str(uuid.uuid4()),
            comment="事件 ID (UUID)",
        ),
        Column(
            "agent_id",
            String(64),
            nullable=True,
            index=True,
            comment="关联 Agent ID",
        ),
        Column(
            "event_type",
            String(50),
            nullable=False,
            index=True,
            comment="事件类型",
        ),
        Column(
            "payload",
            JSON,
            nullable=False,
            default=dict,
            comment="事件负载 (JSON)",
        ),
        Column(
            "created_at",
            DateTime,
            nullable=False,
            default=datetime.now,
            index=True,
            comment="创建时间",
        ),
        Column(
            "read_at",
            DateTime,
            nullable=True,
            comment="已读时间（用于轮询去重）",
        ),
        Column(
            "workflow_id",
            String(36),
            nullable=True,
            index=True,
            comment="关联工作流 ID",
        ),
        Index("idx_events_agent_created", "agent_id", "created_at"),
        Index("idx_events_type_created", "event_type", "created_at"),
        Index("idx_events_workflow", "workflow_id"),
    )
