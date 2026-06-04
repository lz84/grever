"""Human Review API: Pydantic models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class HumanReviewStats(BaseModel):
    disputed_count: int
    waiting_human_count: int
    pending_count: int
    total: int
    recent_pending: List[Dict[str, Any]]

class PendingItem(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    task_id: Optional[str] = None
    input_type: Optional[str] = None
    goal_id: Optional[str] = None
    project_id: Optional[str] = None
    verification_cycle: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class PendingResponse(BaseModel):
    items: List[PendingItem]
    total: int
    page: int
    page_size: int

class BatchRulingItem(BaseModel):
    id: str
    type: str
    ruling: str
    action: str = Field(default="done")

class BatchRulingRequest(BaseModel):
    items: List[BatchRulingItem]
    global_ruling: Optional[str] = Field(default=None)

class BatchRulingResult(BaseModel):
    id: str
    type: str
    success: bool
    message: str
    new_status: Optional[str] = None
    error: Optional[str] = None

class BatchRulingResponse(BaseModel):
    success_count: int
    failed_count: int
    results: List[BatchRulingResult]
