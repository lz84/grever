"""
数据库 SQLAlchemy ORM 模型定义
包含 Grasp 认知表、Reins 任务表、执行日志表
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    JSON,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================================
# Grasp: 认知表
# ============================================================================

class Cognition(Base):
    """
    Grasp 认知表 - 存储系统收集的认知信息
    
    字段:
        id: 认知 ID
        type: 认知类型 (theory, fact, insight, etc.)
        content: 认知内容
        domain: 所属领域
        tags: 标签列表 (JSON)
        confidence: 置信度 (0-1)
        source: 来源
        created_at: 创建时间
        updated_at: 更新时间
    """
    __tablename__ = 'cognitions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(
        Integer, nullable=False, default=0.5, server_default='0.5'
    )
    source: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), index=True
    )
    
    # 索引
    __table_args__ = (
        Index('idx_cognitions_type_domain', 'type', 'domain'),
        Index('idx_cognitions_updated_at', 'updated_at'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'domain': self.domain,
            'tags': self.tags,
            'confidence': self.confidence,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Cognition(id={self.id}, type='{self.type}', domain='{self.domain}')>"


# ============================================================================
# Reins: 任务表
# ============================================================================

class Task(Base):
    """
    Reins 任务表 - 存储任务信息
    
    字段:
        id: 任务 ID
        title: 任务标题
        description: 任务描述
        status: 任务状态 (pending, running, completed, failed, cancelled)
        priority: 优先级 (1-10, 10 为最高)
        parent_id: 父任务 ID (用于嵌套任务)
        created_by: 创建者 ID
        assigned_to: 分配给 (agent ID 或用户 ID)
        created_at: 创建时间
        updated_at: 更新时间
        completed_at: 完成时间
    """
    __tablename__ = 'tasks'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default='pending', index=True
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default='5'
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('tasks.id'), nullable=True, index=True
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关系 - 自引用关系 (不使用 back_populates 避免循环依赖)
    parent: Mapped[Optional['Task']] = relationship(
        'Task',
        foreign_keys='Task.parent_id',
        primaryjoin="Task.id == Task.parent_id",
        uselist=False
    )
    child_tasks: Mapped[List['Task']] = relationship(
        'Task',
        foreign_keys='Task.parent_id',
        primaryjoin="Task.parent_id == Task.id",
        overlaps='parent'  # 避免与 parent 关系冲突
    )
    execution_logs: Mapped[List['ExecutionLog']] = relationship(
        'ExecutionLog', back_populates='task', cascade='all, delete-orphan'
    )
    
    # 索引
    __table_args__ = (
        Index('idx_tasks_status_created', 'status', 'created_at'),
        Index('idx_tasks_parent_id', 'parent_id'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'parent_id': self.parent_id,
            'created_by': self.created_by,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"


class SubTask(Base):
    """
    子任务表 - 用于任务分解和追踪
    
    字段:
        id: 子任务 ID
        task_id: 关联的任务 ID
        title: 子任务标题
        status: 状态 (pending, running, completed, failed)
        result: 执行结果
        created_at: 创建时间
        updated_at: 更新时间
    """
    __tablename__ = 'subtasks'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('tasks.id'), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default='pending', index=True
    )
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    
    # 关系
    task: Mapped['Task'] = relationship('Task')
    
    # 索引
    __table_args__ = (
        Index('idx_subtasks_task_status', 'task_id', 'status'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'title': self.title,
            'status': self.status,
            'result': self.result,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SubTask(id={self.id}, task_id={self.task_id}, title='{self.title}')>"


# ============================================================================
# Workflow: 工作流表
# ============================================================================

class Workflow(Base):
    """
    Workflow 工作流表 - 存储工作流元信息

    字段:
        id: 工作流 ID (UUID 字符串)
        goal_id: 关联的目标 ID
        status: 工作流状态 (draft, running, completed, failed, cancelled)
        name: 工作流名称
        description: 工作流描述
        dag: DAG 结构 (JSON): {"nodes": [step_id, ...], "edges": [[from, to], ...]}
        metadata: 元数据 (JSON)
        created_by: 创建者
        created_at: 创建时间
        updated_at: 更新时间
        started_at: 开始时间
        completed_at: 完成时间
    """
    __tablename__ = 'workflows'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    goal_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default='draft', index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dag: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    steps: Mapped[List['WorkflowStep']] = relationship(
        'WorkflowStep',
        back_populates='workflow',
        cascade='all, delete-orphan',
        foreign_keys='WorkflowStep.workflow_id',
    )

    # 索引
    __table_args__ = (
        Index('idx_workflows_goal_id', 'goal_id'),
        Index('idx_workflows_status_created', 'status', 'created_at'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'status': self.status,
            'name': self.name,
            'description': self.description,
            'dag': self.dag,
            'extra': self.extra,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self) -> str:
        return f"<Workflow(id='{self.id}', name='{self.name}', status='{self.status}')>"


class WorkflowStep(Base):
    """
    WorkflowStep 工作流步骤表 - 存储 DAG 中的节点

    字段:
        id: 步骤 ID (UUID 字符串)
        workflow_id: 关联的工作流 ID
        name: 步骤名称
        description: 步骤描述
        status: 步骤状态 (pending, running, done, failed, skipped, blocked)
        dependencies: 依赖步骤 ID 列表 (JSON) — 前置节点
        order: 在同一层的执行顺序 (拓扑序中的位置)
        agent_id: 负责执行的 Agent ID
        input_data: 输入数据 (JSON)
        output_data: 输出数据 (JSON)
        error: 错误信息
        retry_count: 重试次数
        max_retries: 最大重试次数
        timeout_seconds: 超时秒数
        created_at: 创建时间
        updated_at: 更新时间
        started_at: 开始时间
        completed_at: 完成时间
    """
    __tablename__ = 'workflow_steps'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        String(100), ForeignKey('workflows.id'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default='pending', index=True
    )
    dependencies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    workflow: Mapped['Workflow'] = relationship(
        'Workflow',
        back_populates='steps',
        foreign_keys=[workflow_id],
    )

    # 索引
    __table_args__ = (
        Index('idx_workflow_steps_workflow_id', 'workflow_id'),
        Index('idx_workflow_steps_status', 'status'),
        Index('idx_workflow_steps_workflow_order', 'workflow_id', 'order'),
    )

    def to_dict(self) -> dict:
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

    def __repr__(self) -> str:
        return f"<WorkflowStep(id='{self.id}', name='{self.name}', status='{self.status}')>"


# ============================================================================
# 执行日志表
# ============================================================================

class ExecutionLog(Base):
    """
    执行日志表 - 记录任务执行过程中的操作
    
    字段:
        id: 日志 ID
        task_id: 关联的任务 ID
        agent_id: 执行者 ID (Agent ID)
        action: 执行的行动
        input: 输入参数 (JSON)
        output: 输出结果 (JSON)
        status: 执行状态 (success, failed, error, skipped)
        duration_ms: 执行耗时 (毫秒)
        created_at: 创建时间
    """
    __tablename__ = 'execution_logs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('tasks.id'), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(500), nullable=False)
    input: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default='success', index=True
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default='0'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), index=True
    )
    
    # 关系
    task: Mapped['Task'] = relationship('Task', back_populates='execution_logs')
    
    # 索引
    __table_args__ = (
        Index('idx_execution_logs_task_created', 'task_id', 'created_at'),
        Index('idx_execution_logs_status', 'status'),
        Index('idx_execution_logs_agent_created', 'agent_id', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'action': self.action,
            'input': self.input,
            'output': self.output,
            'status': self.status,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, task_id={self.task_id}, action='{self.action}')>"
