"""
Workflow 数据模型

定义 Workflow 和 WorkflowStep 的 SQLAlchemy ORM 模型，
支持 DAG（有向无环图）结构的工作流编排。
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from pydantic import BaseModel

from .base import Base

# ============================================================================
# 枚举
# ============================================================================

class WorkflowStatus(str):
    """工作流状态"""
    DRAFT = 'draft'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    BLOCKED = 'blocked'  # MA-K233: 新增 BLOCKED 状态

class WorkflowStepStatus(str):
    """工作流步骤状态"""
    PENDING = 'pending'
    RUNNING = 'running'
    DONE = 'done'
    FAILED = 'failed'
    SKIPPED = 'skipped'
    BLOCKED = 'blocked'

# ============================================================================
# Pydantic 请求/响应模型
# ============================================================================

class WorkflowCreate(BaseModel):
    """创建工作流请求"""
    name: str
    description: Optional[str] = None
    goal_id: Optional[str] = None
    created_by: Optional[str] = None

class WorkflowUpdate(BaseModel):
    """更新工作流请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    dag: Optional[dict] = None
    workflow_metadata: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class WorkflowResponse(BaseModel):
    """工作流响应"""
    id: str
    goal_id: Optional[str] = None
    status: str
    name: str
    description: Optional[str] = None
    dag: Optional[dict] = None
    workflow_metadata: Optional[dict] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: List['WorkflowStepResponse'] = []

    class Config:
        from_attributes = True

class WorkflowStepCreate(BaseModel):
    """创建工作流步骤请求"""
    workflow_id: str
    name: str
    description: Optional[str] = None
    dependencies: Optional[List[str]] = None
    order: Optional[int] = None
    agent_id: Optional[str] = None
    input_data: Optional[dict] = None
    timeout_seconds: Optional[int] = None

class WorkflowStepUpdate(BaseModel):
    """更新工作流步骤请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    dependencies: Optional[List[str]] = None
    order: Optional[int] = None
    agent_id: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error: Optional[str] = None
    retry_count: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class WorkflowStepResponse(BaseModel):
    """工作流步骤响应"""
    id: str
    workflow_id: str
    name: str
    description: Optional[str] = None
    status: str
    dependencies: Optional[List[str]] = None
    order: Optional[int] = None
    agent_id: Optional[str] = None
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ============================================================================
# SQLAlchemy ORM 模型
# ============================================================================

def _generate_id():
    return str(uuid.uuid4())

class Workflow(Base):
    """
    Workflow 工作流表

    存储工作流元信息和 DAG 结构。
    DAG 格式: {"nodes": ["step_id1", ...], "edges": [["from_id", "to_id"], ...]}
    """
    __tablename__ = 'workflows'

    id = Column(String(36), primary_key=True, default=_generate_id)
    goal_id = Column(String(36), nullable=True, index=True, comment="关联目标 ID")
    status = Column(String(20), nullable=False, default='draft', index=True,
                    comment="工作流状态")
    name = Column(String(500), nullable=False, comment="工作流名称")
    description = Column(Text, nullable=True, comment="工作流描述")
    dag = Column(JSON, nullable=True, comment="DAG 结构")
    workflow_metadata = Column(JSON, nullable=True, comment="元数据")
    created_by = Column(String(200), nullable=True, comment="创建者")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # Sprint 22 新增字段
    project_id = Column(String(36), nullable=True, comment="所属 Project（Project 级 Workflow）")
    parent_scenario_id = Column(String(36), nullable=True, comment="来源 Scenario")
    level = Column(String(20), nullable=True, comment="level: 'goal' 或 'project'")

    # 关系
    steps = relationship(
        'WorkflowStep',
        back_populates='workflow',
        cascade='all, delete-orphan',
        foreign_keys='WorkflowStep.workflow_id',
        order_by='WorkflowStep.order',
    )

    __table_args__ = (
        Index('idx_workflows_goal_id', 'goal_id'),
        Index('idx_workflows_status_created', 'status', 'created_at'),
        Index('idx_workflows_project_id', 'project_id'),
        Index('idx_workflows_parent_scenario_id', 'parent_scenario_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'status': self.status,
            'name': self.name,
            'description': self.description,
            'dag': self.dag,
            'workflow_metadata': self.workflow_metadata,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'step_count': len(self.steps) if self.steps else 0,
            'project_id': self.project_id,
            'parent_scenario_id': self.parent_scenario_id,
            'level': self.level,
        }

    def __repr__(self):
        return f"<Workflow(id='{self.id}', name='{self.name}', status='{self.status}')>"

class WorkflowStep(Base):
    """
    WorkflowStep 工作流步骤表

    存储 DAG 中的节点。每个步骤可以：
    - 指定前置依赖（dependencies）
    - 分配到特定 Agent
    - 重试（max_retries）
    - 超时（timeout_seconds）
    """
    __tablename__ = 'workflow_steps'

    id = Column(String(36), primary_key=True, default=_generate_id)
    workflow_id = Column(
        String(36), ForeignKey('workflows.id'), nullable=False, index=True
    )
    name = Column(String(500), nullable=False, comment="步骤名称")
    description = Column(Text, nullable=True, comment="步骤描述")
    status = Column(String(20), nullable=False, default='pending', index=True,
                    comment="步骤状态")
    dependencies = Column(JSON, nullable=True, comment="依赖步骤 ID 列表")
    order = Column(Integer, nullable=True, index=True, comment="执行顺序")
    agent_id = Column(String(200), nullable=True, comment="执行 Agent ID")
    input_data = Column(JSON, nullable=True, comment="输入数据")
    output_data = Column(JSON, nullable=True, comment="输出数据")
    error = Column(Text, nullable=True, comment="错误信息")
    retry_count = Column(Integer, nullable=False, default=0, comment="重试次数")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重试次数")
    timeout_seconds = Column(Integer, nullable=True, comment="超时秒数")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 关系
    workflow = relationship(
        'Workflow',
        back_populates='steps',
        foreign_keys=[workflow_id],
    )

    __table_args__ = (
        Index('idx_workflow_steps_workflow_id', 'workflow_id'),
        Index('idx_workflow_steps_status', 'status'),
        Index('idx_workflow_steps_workflow_order', 'workflow_id', 'order'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'dependencies': self.dependencies,
            'order': self.order,
            'agent_id': self.agent_id,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'error': self.error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'timeout_seconds': self.timeout_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return (f"<WorkflowStep(id='{self.id}', name='{self.name}', "
                f"status='{self.status}', order={self.order})>")
