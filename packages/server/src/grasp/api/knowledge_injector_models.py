"""知识注入 API - Pydantic 模型"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TaskResultInput(BaseModel):
    """单个任务执行结果"""
    task_id: str = Field(..., description="任务 ID")
    task_title: str = Field(..., description="任务标题")
    status: str = Field(..., description="任务状态: completed, failed, cancelled")
    agent_id: Optional[str] = Field(None, description="执行 Agent ID")
    agent_name: Optional[str] = Field(None, description="执行 Agent 名称")
    workflow_id: Optional[str] = Field(None, description="所属工作流 ID")
    goal_id: Optional[str] = Field(None, description="关联目标 ID")
    project_id: Optional[str] = Field(None, description="关联项目 ID")
    started_at: Optional[str] = Field(None, description="开始时间 ISO 8601")
    completed_at: Optional[str] = Field(None, description="完成时间 ISO 8601")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息（失败时）")
    output_summary: Optional[str] = Field(None, description="输出摘要")
    tags: Optional[List[str]] = Field(None, description="标签")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")

class WorkflowResultInput(BaseModel):
    """工作流执行结果"""
    workflow_id: str = Field(..., description="工作流 ID")
    workflow_name: str = Field(..., description="工作流名称")
    goal_id: Optional[str] = Field(None, description="关联目标 ID")
    status: str = Field(..., description="工作流状态: completed, failed, cancelled")
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    started_at: Optional[str] = Field(None, description="开始时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    duration_ms: Optional[int] = Field(None, description="总耗时（毫秒）")
    task_results: Optional[List[TaskResultInput]] = Field(None, description="各任务结果")
    disputes_resolved: Optional[int] = Field(None, description="解决的争议数")
    tags: Optional[List[str]] = Field(None, description="标签")

class DisputeResultInput(BaseModel):
    """争议解决结果"""
    dispute_id: str = Field(..., description="争议 ID")
    dispute_type: str = Field(..., description="争议类型")
    resolution: str = Field(..., description="解决方式")
    task_id: Optional[str] = Field(None, description="关联任务 ID")
    agent_ids: Optional[List[str]] = Field(None, description="涉及的 Agent ID 列表")
    resolution_time_ms: Optional[int] = Field(None, description="解决耗时")
    summary: Optional[str] = Field(None, description="争议摘要")
    lesson_learned: Optional[str] = Field(None, description="学到的教训")

class InjectResponse(BaseModel):
    """注入响应"""
    status: str
    cognition_id: str
    cognition_type: str
    message: str

class InjectHistoryItem(BaseModel):
    """注入历史记录项"""
    id: str
    source_type: str  # task, workflow, dispute
    source_id: str
    cognition_id: str
    cognition_type: str
    created_at: str
    status: str
