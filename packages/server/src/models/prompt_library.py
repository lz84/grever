"""Prompt Library 模型 - 统一 AI 交互服务的 prompt 模板管理"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.orm import relationship
from .base import Base


def _generate_prompt_id():
    return f"prompt-{uuid.uuid4().hex[:12]}"


class PromptLibrary(Base):
    """Prompt 模板库 - 统一 AI 交互服务的 prompt 管理"""
    __tablename__ = 'prompt_library'

    id = Column(String(32), primary_key=True)
    # 交互编号，如 E-1, E-3, SR-1, V-1, DP-1, KF-1
    
    version = Column(Integer, default=1, nullable=False)
    # 模板版本号，用于迭代更新
    
    content = Column(Text, nullable=False)
    # prompt 模板内容，包含 {变量} 占位符
    
    context_schema = Column(Text, nullable=False)
    # JSON 格式：定义所需上下文变量的 schema
    
    category = Column(String(50), nullable=True)
    # 交互类别：planning / self_review / verification / dispatch / knowledge
    
    description = Column(Text, nullable=True)
    # 模板用途描述
    
    output_schema = Column(Text, nullable=True)
    # JSON 格式：期望的 JSON 输出 schema
    
    status = Column(String(16), default='active')
    # active / deprecated / draft
    
    created_at = Column(String(50), nullable=True)
    updated_at = Column(String(50), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        import json
        
        def _parse_json(value):
            if not value:
                return None
            if isinstance(value, (dict, list)):
                return value
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        
        return {
            'id': self.id,
            'version': self.version,
            'content': self.content,
            'context_schema': _parse_json(self.context_schema),
            'category': self.category,
            'description': self.description,
            'output_schema': _parse_json(self.output_schema),
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
