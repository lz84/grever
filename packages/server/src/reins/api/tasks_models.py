"""Task API Pydantic models — extracted from tasks.py"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ============ MAK-215: 请求/响应模型 ============

class CompleteTaskRequest(BaseModel):
    """任务完成请求(P1: 必须传入执行证据)"""
    status: str = Field(default="done", description="任务状态,目前只支持 'done'")
    result: str = Field(..., description="执行结果描述(必填,至少5字符)")
    execution_log: Dict[str, Any] = Field(..., description="执行日志证据(必填,非空字典)")
    duration_ms: int = Field(..., gt=0, description="实际执行耗时毫秒(必填,必须>0)")
    output: Optional[Dict[str, Any]] = Field(default=None, description="执行输出")
    artifacts: Optional[List[str]] = Field(default=None, description="产物列表")
    confidence: Optional[float] = Field(default=None, description="置信度")
    issues_encountered: Optional[List[str]] = Field(default=None, description="遇到的问题")

class ScenarioEvolutionResult(BaseModel):
    """场景进化结果"""
    evaluated: bool = False
    assessment: Optional[str] = None
    version_upgraded: bool = False
    new_version: Optional[str] = None
    status_changed: bool = False
    new_status: Optional[str] = None
    reason: Optional[str] = None

class CompleteTaskResponse(BaseModel):
    """任务完成响应"""
    success: bool
    task_id: str
    goal_progress: Optional[dict] = None
    scenario_feedback_triggered: Optional[bool] = None
    scenario_evolution_result: Optional[ScenarioEvolutionResult] = None

class FailTaskRequest(BaseModel):
    """任务失败请求(P1: 支持传入执行证据)"""
    error_type: str
    error_message: str
    retry_count: int
    max_retries: int
    execution_log: Optional[Dict[str, Any]] = Field(default=None, description="执行日志证据(可选)")
    duration_ms: Optional[int] = Field(default=None, description="实际执行耗时毫秒(可选)")

class FailTaskResponse(BaseModel):
    """任务失败响应"""
    success: bool
    task_id: str
    next_action: str  # "retry" or "blocked"
    retry_count: int
    max_retries: int
    delay_seconds: Optional[int] = None

# ---- P5-03-05: Task 批量状态变更 ----

class BatchStatusUpdate(BaseModel):
    task_ids: List[int]
    status: str
    reason: Optional[str] = None

class BatchUpdateResponse(BaseModel):
    updated: int
    failed: List[dict]

# ---- Task 状态更新 ----

class TaskStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="目标状态")

# ---- P5-03-06: Task 阻塞机制 ----

class BlockTaskRequest(BaseModel):
    reason: str = "Blocked by system"

class UnblockTaskRequest(BaseModel):
    reason: Optional[str] = None

class TaskAssignRequest(BaseModel):
    """POST /api/v1/tasks/{task_id}/assign"""
    agent_id: str

# ---- P5-03-07: Task 状态历史记录 ----

class ActivityLogResponse(BaseModel):
    id: str
    task_id: str
    old_status: str
    new_status: str
    reason: Optional[str]
    actor: Optional[str]
    timestamp: str

# ---- 统一任务状态列表 ----

class TaskStatusItem(BaseModel):
    value: str
    label: str
    category: str
    color: str

# ============ MAK-235: 任务失败重试机制 ============

class FailureLogEntry(BaseModel):
    """失败日志条目"""
    id: str
    task_id: str
    error_type: str
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    timestamp: str

class FailureLogResponse(BaseModel):
    """失败日志响应"""
    task_id: int
    failures: List[FailureLogEntry]

class RetryRequest(BaseModel):
    """手动重试请求"""
    reason: Optional[str] = None

class RetryResponse(BaseModel):
    """手动重试响应"""
    success: bool
    task_id: str
    message: str
    retry_count: int
    status: str

# ---- P1-01: Agent 主动上报任务进度 ----

class TaskProgressRequest(BaseModel):
    """任务进度上报请求"""
    progress_percent: Optional[float] = Field(None, description="进度百分比 0-100")
    current_step: Optional[str] = Field(None, description="当前步骤")
    message: Optional[str] = Field(None, description="进度消息")
    metadata: Optional[dict] = Field(None, description="额外元数据")

class TaskProgressResponse(BaseModel):
    """任务进度上报响应"""
    success: bool
    task_id: str
    progress_percent: Optional[float] = None

# ---- 人工审核 API ----

class ReviewTaskRequest(BaseModel):
    """人工审核请求"""
    action: str = Field(..., description="操作:approve(通过)或 reject(驳回)")
    reason: Optional[str] = Field(None, description="驳回原因(可选)")

class ReviewTaskResponse(BaseModel):
    success: bool
    task_id: str
    new_status: str
    message: str

# ---- VERIFIER AGENT API ----

class SetVerifierRequest(BaseModel):
    """设置验证 Agent 请求"""
    verifier_agent_id: str

class GetEffectiveVerifierResponse(BaseModel):
    """获取有效验证 Agent 响应"""
    task_id: str
    effective_verifier: str
    inheritance_chain: dict

# ---- Ruling ----

class RulingRequest(BaseModel):
    ruling: str
    action: str  # done | in_progress | verifying

# ---- Sprint 76: 暂停/恢复 API ----

class PauseTaskResponse(BaseModel):
    success: bool
    task_id: str
    status: str
    paused_reason: str

class ResumeTaskResponse(BaseModel):
    success: bool
    task_id: str
    status: str
    paused_reason: Optional[str]

class RestartTaskRequest(BaseModel):
    """重启任务请求"""
    reason: Optional[str] = Field(None, description="重启原因(可选)")

class RestartTaskResponse(BaseModel):
    """重启任务响应"""
    success: bool
    task_id: str
    old_status: str
    new_status: str = "in_progress"
    assigned_agent: Optional[str]
