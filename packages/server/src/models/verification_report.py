"""Verification Report 模型 — Project/Goal 级统筹验证报告"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.orm import relationship
from .base import Base


def _generate_vr_id():
    return f"vr-{uuid.uuid4().hex[:12]}"


class VerificationReport(Base):
    """统筹验证报告"""
    __tablename__ = 'verification_reports'

    id = Column(String(36), primary_key=True, default=_generate_vr_id)
    
    # 验证层级
    level = Column(String(20), nullable=False, default='project')
    # project | goal
    
    # 关联目标
    target_id = Column(String(36), nullable=False, index=True)
    
    # 验证者 Agent ID
    verifier_id = Column(String(32), nullable=False)
    
    # 轮次（每复测 +1）
    round = Column(Integer, nullable=False, default=1)
    
    # 结论
    verdict = Column(String(20), nullable=False)
    # passed | failed | partial
    
    # 摘要
    summary = Column(Text, nullable=True)
    
    # 各 Task 结果汇总（JSON）
    task_results = Column(Text, nullable=True)
    
    # 发现的空白 [{gap, severity}]（JSON）
    gaps = Column(Text, nullable=True)
    
    # 建议列表（JSON/Text array）
    recommendations = Column(Text, nullable=True)
    
    # 补救任务建议（JSON）
    remedial_tasks = Column(Text, nullable=True)
    
    # 验证时的完整上下文
    raw_context = Column(Text, nullable=True)
    
    # 时间戳
    created_at = Column(String(50), nullable=True)

    def to_dict(self):
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
            'level': self.level,
            'target_id': self.target_id,
            'verifier_id': self.verifier_id,
            'round': self.round,
            'verdict': self.verdict,
            'summary': self.summary,
            'task_results': _parse_json(self.task_results),
            'gaps': _parse_json(self.gaps),
            'recommendations': _parse_json(self.recommendations),
            'remedial_tasks': _parse_json(self.remediative_tasks),
            'raw_context': self.raw_context,
            'created_at': self.created_at,
        }
