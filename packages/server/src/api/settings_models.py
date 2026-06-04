"""Settings API - Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, Field

class ConfigItemResponse(BaseModel):
    """单个配置项响应"""
    key: str
    value: str
    type: str
    description: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

class ConfigValueUpdate(BaseModel):
    """配置值更新请求"""
    value: str

class BatchUpdateRequest(BaseModel):
    """批量更新请求"""
    configs: dict = Field(default_factory=dict)

class TestConnectionResponse(BaseModel):
    """连接测试结果"""
    status: str
    message: str
    gateway_url: Optional[str] = None
    response_time_ms: Optional[int] = None
    details: Optional[dict] = None

class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: Optional[str] = None
    provider: Optional[str] = None
