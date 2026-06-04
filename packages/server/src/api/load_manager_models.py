"""负载管理 API - Pydantic 模型"""

from pydantic import BaseModel
from typing import Optional

class LoadConfig(BaseModel):
    """负载配置"""
    max_concurrent_tasks: int = 5
    load_threshold: int = 80
    recovery_threshold: int = 50

class LoadConfigResponse(BaseModel):
    """负载配置响应"""
    agent_id: str
    max_concurrent_tasks: int
    load_threshold: int
    recovery_threshold: int

class CurrentLoadResponse(BaseModel):
    """当前负载响应"""
    agent_id: str
    current_tasks: int
    current_load: int
    is_overloaded: bool
    pending_tasks_count: int
    load_threshold: int
    recovery_threshold: int

class PendingTasksResponse(BaseModel):
    """待领取任务响应"""
    agent_id: str
    pending_tasks: list
    total_count: int
    is_overloaded: bool

class AgentListItem(BaseModel):
    """Agent 列表项（包含负载信息）"""
    id: str
    name: str
    status: str
    health_status: str
    address: Optional[str]
    load: int
    current_tasks: int
    max_concurrent_tasks: int
    consecutive_offline_count: int
    model_name: str
    last_heartbeat: Optional[str]
    registered_at: Optional[str]
    capabilities: list
