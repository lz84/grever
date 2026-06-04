"""
成果物 Pydantic 模型
从 artifacts.py 拆分
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class ArtifactCreate(BaseModel):
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    goal_id: Optional[str] = None
    created_by: str = Field(..., description="生成的 Agent ID")
    name: str = Field(..., description="文件名")
    type: str = Field(default="other", description="类型: document/code/image/data/other")
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    content_base64: Optional[str] = Field(default=None, description="文件内容 base64 编码")

class ArtifactUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class ArtifactResponse(BaseModel):
    id: str
    task_id: Optional[str]
    project_id: Optional[str]
    goal_id: Optional[str]
    created_by: str
    name: str
    type: str
    url: Optional[str]
    size: int
    description: Optional[str]
    tags: Optional[List[str]]
    created_at: str

class ArtifactListResponse(BaseModel):
    artifacts: List[ArtifactResponse]
    total: int
