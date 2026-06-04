"""Task model — ORM + auto-generated Pydantic schemas"""

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional
from .base import Base
from .schema_factory import auto_schema
from .human_input import HumanInputRequest  # noqa: F401 - ensures SQLAlchemy can resolve relationship

class TaskStatus(str):
    """Task 数据库状态（唯一真实数据源）。禁止添加不在此列表的值。详见 DEV-GUIDE.md §状态管理规范"""
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    PAUSED = 'paused'          # 人为暂停/异常中断
    WAITING = 'waiting'        # 等待前置任务/Project完成
    REVIEW_NEEDED = 'review_needed'
    WAITING_HUMAN = 'waiting_human'  # Sprint 89: HITL 等待人工输入

    @classmethod
    def all(cls):
        return [cls.TODO, cls.IN_PROGRESS, cls.DONE, cls.FAILED, cls.TIMEOUT, cls.PAUSED, cls.WAITING, cls.REVIEW_NEEDED, cls.WAITING_HUMAN]

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls.all()

class TaskPriority(str):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

class TaskType(str):
    RESEARCH = 'research'
    CODING = 'coding'
    REVIEW = 'review'
    OTHER = 'other'

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(String(32), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String(5000), nullable=True)
    status = Column(String(20), default='todo')
    priority = Column(String(20), default='medium')
    # capability_tags: JSON object replacing category (business, professional, technical, management)
    capability_tags = Column(Text, nullable=True, default='{}')
    due_date = Column(DateTime, nullable=True)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()), onupdate=lambda: int(datetime.utcnow().timestamp()))
    assigned_agent = Column(String(32), nullable=True)
    started_at = Column(Integer, nullable=True)
    completed_at = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    project_id = Column(String(36), nullable=True)
    goal_id = Column(String(36), nullable=True)

    # 关联的 Workflow 步骤
    workflow_step_id = Column(String(36), nullable=True)

    # 依赖关系：JSON 数组，存储依赖的 task id 列表
    depends_on = Column(Text, nullable=True)  # JSON array: ["task-xxx", ...]
    # Sprint 79: forward-link for DAG drawing (derived from depends_on)
    next_step = Column(Text, default='[]')  # JSON array of task IDs that depend on this task

    # Failure info
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    blocked_reason = Column(Text, nullable=True)
    result_summary = Column(Text, nullable=True)
    result = Column(String(5000), nullable=True)

    # Sprint 76: paused 状态原因（人类主动暂停 or 孤儿任务）
    # 'human' — 人类主动暂停
    # 'orphan_on_restart' — server 重启时发现 in_progress 孤儿
    # 'orphan_on_offline' — agent 离线时发现孤儿
    # 'orphan_on_timeout' — 任务超时自动暂停
    # NULL — 正常任务（不是 paused）
    paused_reason = Column(String(50), nullable=True)
    
    # Verification cycle tracking (Sprint 54)
    verification_cycle = Column(Integer, default=0)
    ruling_comment_id = Column(String(36), nullable=True)
    instruction_comment_id = Column(String(36), nullable=True)
    ruling_instruction = Column(Text, nullable=True)

    # Sprint 50-52: acceptance criteria（验收标准，JSON 格式）
    acceptance_criteria = Column(Text, nullable=True)

    # Sprint 86: delivery criteria（交付标准，JSON 格式）
    delivery_criteria = Column(Text, nullable=True)

    # Sprint 53: verifier agent (three-level inheritance)
    verifier_agent_id = Column(String(32), nullable=True)

    # Sprint 66: 验证强制 — 是否需要验证（默认需要）
    needs_verification = Column(Boolean, default=True, nullable=False)

    # Doc Refs Mode (replace stuffing full docs into prompt → agent reads via read tool)
    doc_refs = Column(Text, nullable=True)  # JSON array: ["docs/plan.md#section1"]
    workspace_path = Column(String(500), nullable=True)  # inherited from Project/Goal
    # Sprint 86: 三级上下文文档
    context_md = Column(Text, nullable=True)

    executor_type = Column(String(20), nullable=False, default='ai')  # ai/human/hybrid

    # Relationships
    # Sprint 77 P1-1: goal_id 已从 DB 删除（通过 project_id→goal_id 推导）
    parent_id = Column(String(32), ForeignKey('tasks.id'), nullable=True)
    children = relationship('Task', back_populates='parent', cascade='all, delete-orphan')
    parent = relationship('Task', back_populates='children', remote_side=[id])
    dependencies = relationship('TaskDependency', back_populates='task', cascade='all, delete-orphan', foreign_keys='[TaskDependency.task_id]')
    human_input_requests = relationship('HumanInputRequest', back_populates='task', cascade='all, delete-orphan')

    @staticmethod
    def _to_iso_datetime(value):
        """Convert integer timestamp or datetime string to ISO format."""
        if not value:
            return None
        if isinstance(value, int):
            try:
                return datetime.utcfromtimestamp(value).isoformat()
            except (OSError, ValueError):
                return None
        if isinstance(value, str):
            return value
        return None

    def to_dict(self):
        # Priority: DB 可能存整数(0/1/2/3)或字符串，统一转字符串
        raw_priority = self.priority
        if isinstance(raw_priority, int):
            _priority_map = {0: 'critical', 1: 'high', 2: 'medium', 3: 'low'}
            priority_str = _priority_map.get(raw_priority, 'medium')
        else:
            priority_str = raw_priority if raw_priority else 'medium'
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': priority_str,
            'capability_tags': self._parse_capability_tags(),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'goal_id': self.goal_id,
            'parent_id': self.parent_id,
            'assigned_agent': self.assigned_agent,
            'project_id': getattr(self, 'project_id', None),
            'workflow_step_id': getattr(self, 'workflow_step_id', None),
            'retry_count': self.retry_count or 0,
            'max_retries': self.max_retries or 3,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'blocked_reason': self.blocked_reason,
            'result_summary': self.result_summary,
            'result': self.result,
            'paused_reason': getattr(self, 'paused_reason', None),
            'acceptance_criteria': self.acceptance_criteria,
            'delivery_criteria': getattr(self, 'delivery_criteria', None),
            'verifier_agent_id': getattr(self, 'verifier_agent_id', None),
            'needs_verification': getattr(self, 'needs_verification', True),
            'doc_refs': getattr(self, 'doc_refs', None),
            'workspace_path': getattr(self, 'workspace_path', None),
            'context_md': getattr(self, 'context_md', None),
            'executor_type': getattr(self, 'executor_type', 'ai'),
            'verification_cycle': getattr(self, 'verification_cycle', 0),
            'ruling_comment_id': getattr(self, 'ruling_comment_id', None),
            'instruction_comment_id': getattr(self, 'instruction_comment_id', None),
            'ruling_instruction': getattr(self, 'ruling_instruction', None),
            'dependency_ids': [d.dependency_id for d in self.dependencies if d is not None and d.dependency_id] if self.dependencies else [],
            'depends_on': self._parse_depends_on(),
            'next_step': self._parse_next_step(),
        }

    def _parse_depends_on(self):
        """Parse depends_on JSON field"""
        if not self.depends_on:
            return []
        try:
            return json.loads(self.depends_on) if isinstance(self.depends_on, str) else self.depends_on
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_next_step(self):
        """Parse next_step JSON field"""
        if not self.next_step:
            return []
        try:
            return json.loads(self.next_step) if isinstance(self.next_step, str) else self.next_step
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_capability_tags(self):
        """Parse capability_tags JSON field"""
        if not self.capability_tags:
            return {}
        try:
            return json.loads(self.capability_tags) if isinstance(self.capability_tags, str) else self.capability_tags
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"

# Auto-generated Pydantic schemas from ORM columns
from typing import Union as TypingUnion, List as TypingList, Any as TypingAny
from pydantic import create_model

_TaskCreateBase, _TaskUpdateBase, TaskResponseBase = auto_schema(
    Task,
    create_defaults={'status': 'todo', 'priority': 'medium', 'retry_count': 0, 'max_retries': 3},
)

# Sprint 86: 统一依赖关系字段
# 用户只通过 depends_on 设置依赖（不再暴露 dependency_ids 作为输入）
# depends_on 写入时自动同步三处：JSON列 + task_dependencies表 + next_step
TaskCreate = create_model(
    'TaskCreate',
    __base__=_TaskCreateBase,
    depends_on=(TypingList[TypingAny], ...),  # Required: DAG 依赖顺序
    capability_tags=(dict, ...),  # Required: 四维标签，匹配引擎输入
    context_md=(Optional[str], None),  # Sprint 86: 三级上下文文档
    strict_mode=(bool, True),  # Sprint 98: True=缺失前置阻断, False=自动补全
)

TaskUpdate = create_model(
    'TaskUpdate',
    __base__=_TaskUpdateBase,
    depends_on=(Optional[TypingUnion[str, TypingList[TypingAny]]], None),
    capability_tags=(Optional[TypingUnion[str, TypingList[TypingAny], dict]], None),
    context_md=(Optional[str], None),  # Sprint 86: 三级上下文文档
    strict_mode=(Optional[bool], True),  # Sprint 98: True=缺失前置阻断, False=自动补全
)

# Response 保留 dependency_ids 为只读字段（从关系表推导）
TaskResponse = create_model(
    'TaskResponse',
    __base__=TaskResponseBase,
    dependency_ids=(TypingList[str], []),
    depends_on=(Optional[TypingList[TypingAny]], []),
    next_step=(Optional[TypingList[TypingAny]], []),
    capability_tags=(Optional[dict], {}),
    context_md=(Optional[str], None),  # Sprint 86: 三级上下文文档
)

class TaskDependency(Base):
    __tablename__ = 'task_dependencies'

    task_id = Column(String(32), ForeignKey('tasks.id'), primary_key=True)
    dependency_id = Column(String(32), ForeignKey('tasks.id'), primary_key=True)

    task = relationship('Task', foreign_keys=[task_id], back_populates='dependencies')
    dependency = relationship('Task', foreign_keys=[dependency_id])

    def __repr__(self):
        return f"<TaskDependency(task_id={self.task_id}, dependency_id={self.dependency_id})>"
