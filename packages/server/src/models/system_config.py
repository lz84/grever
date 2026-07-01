"""System Config model — ORM + auto-generated Pydantic schemas"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from typing import Optional
from .base import Base
from .schema_factory import auto_schema


class SystemConfig(Base):
    """系统配置表 ORM 模型"""
    __tablename__ = 'system_config'

    id = Column(String(36), primary_key=True, default=lambda: f"cfg-{__import__('uuid').uuid4().hex[:12]}")
    category = Column(String(50), nullable=False, index=True)  # 分类: gateway, agent, task, etc.
    key = Column(String(100), nullable=False, index=True)  # 配置项 key
    value = Column(Text, nullable=True)  # 配置值 (JSON string or plain text)
    description = Column(Text, nullable=True)  # 配置描述
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True, default='system')  # 最后更新人

    def to_dict(self):
        import json
        # 尝试解析 value 为 JSON
        value_data = self.value
        if value_data:
            try:
                value_data = json.loads(value_data) if isinstance(value_data, str) else value_data
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': value_data,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }

    def __repr__(self):
        return f"<SystemConfig(category='{self.category}', key='{self.key}')>"


# Auto-generated Pydantic schemas from ORM columns
SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse = auto_schema(
    SystemConfig,
)
