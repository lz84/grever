"""
TraceEvent 和 TraceReport 模型定义 - P5-08 Trace 增强
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    JSON,
    Float,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .models import Base


# ============================================================================
# TraceEvent: Execution Trace 表 (P5-08)
# ============================================================================

class TraceEvent(Base):
    """
    TraceEvent 表 - P5-08 Trace 增强：持久化执行追踪事件
    
    字段:
        id: 事件 ID (UUID)
        event_type: 事件类型 (task_started/task_completed/task_failed/state_changed/agent_input/agent_output/error/context_injected)
        workflow_id: 工作流 ID
        task_id: 任务 ID
        agent_id: 执行 Agent ID (P5-08-03: Agent 归属)
        timestamp: 事件时间
        duration_ms: 事件耗时 (P5-08-02: 步骤耗时计算)
        data: 通用数据 (JSON)
        from_state: 原状态 (状态变更专用)
        to_state: 新状态 (状态变更专用)
        input_data: 输入数据 (JSON, Agent 输入输出专用)
        output_data: 输出数据 (JSON, Agent 输入输出专用)
        error_message: 错误消息
        error_type: 错误类型
        created_at: 创建时间
    """
    __tablename__ = 'trace_events'
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)  # P5-08-03
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')  # P5-08-02
    
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    from_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    to_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    
    # 索引
    __table_args__ = (
        Index('idx_trace_events_task_timestamp', 'task_id', 'timestamp'),
        Index('idx_trace_events_workflow_task', 'workflow_id', 'task_id'),
        Index('idx_trace_events_agent_timestamp', 'agent_id', 'timestamp'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'event_type': self.event_type,
            'workflow_id': self.workflow_id,
            'task_id': self.task_id,
            'agent_id': self.agent_id,  # P5-08-03
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'duration_ms': self.duration_ms,  # P5-08-02
            'data': self.data,
            'from_state': self.from_state,
            'to_state': self.to_state,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'error_message': self.error_message,
            'error_type': self.error_type,
        }
    
    def __repr__(self) -> str:
        return f"<TraceEvent(id='{self.id}', event_type='{self.event_type}', task_id='{self.task_id}')>"


# ============================================================================
# TraceReport: Execution Report 表 (P5-08)
# ============================================================================

class TraceReport(Base):
    """
    TraceReport 表 - P5-08 Trace 增强：持久化执行报告
    
    字段:
        id: 报告 ID (UUID)
        workflow_id: 工作流 ID
        task_id: 任务 ID
        task_title: 任务标题
        started_at: 开始时间
        completed_at: 完成时间
        total_duration_ms: 总耗时 (P5-08-02)
        final_state: 最终状态
        success: 是否成功
        steps: 执行步骤列表 (JSON, 包含耗时)
        cognitions_used: 认知使用数
        context_size_bytes: 上下文大小
        result: 执行结果 (JSON)
        error_message: 错误消息
        error_stack: 错误堆栈 (P5-08)
        cpu_time_ms: CPU耗时 (P5-08)
        memory_peak_mb: 内存峰值 (P5-08)
        io_read_bytes: IO读取字节数 (P5-08)
        io_write_bytes: IO写入字节数 (P5-08)
        network_bytes: 网络传输字节数 (P5-08)
        generated_at: 生成时间
    """
    __tablename__ = 'trace_reports'
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_title: Mapped[str] = mapped_column(String(500), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # P5-08-02
    
    final_state: Mapped[str] = mapped_column(String(100), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 包含耗时的步骤列表
    cognitions_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # P5-08: 错误堆栈和资源使用
    error_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cpu_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memory_peak_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    io_read_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    io_write_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    network_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    
    # 索引
    __table_args__ = (
        Index('idx_trace_reports_task_id', 'task_id'),
        Index('idx_trace_reports_workflow_id', 'workflow_id'),
        Index('idx_trace_reports_started_at', 'started_at'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'task_id': self.task_id,
            'task_title': self.task_title,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration_ms': self.total_duration_ms,  # P5-08-02
            'final_state': self.final_state,
            'success': self.success,
            'steps': self.steps,
            'cognitions_used': self.cognitions_used,
            'context_size_bytes': self.context_size_bytes,
            'result': self.result,
            'error_message': self.error_message,
            # P5-08
            'error_stack': self.error_stack,
            'cpu_time_ms': self.cpu_time_ms,
            'memory_peak_mb': self.memory_peak_mb,
            'io_read_bytes': self.io_read_bytes,
            'io_write_bytes': self.io_write_bytes,
            'network_bytes': self.network_bytes,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<TraceReport(id='{self.id}', task_id='{self.task_id}', success={self.success})>"
