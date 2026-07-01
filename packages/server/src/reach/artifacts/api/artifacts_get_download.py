"""
成果物获取与下载端点
从 artifacts.py 拆分
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import Artifact
from .artifacts_models import ArtifactResponse
from .artifacts_helpers import _row_to_artifact

router = APIRouter()

@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """获取成果物详情"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()

    if not artifact:
        raise HTTPException(404, "Artifact not found")

    return ArtifactResponse(
        id=artifact.id,
        name=artifact.name,
        description=artifact.description,
        storage_path=artifact.storage_path,
        mime_type=artifact.mime_type,
        size_bytes=artifact.size_bytes,
        task_id=artifact.task_id,
        project_id=artifact.project_id,
        goal_id=artifact.goal_id,
        created_by=artifact.created_by,
        created_at=str(artifact.created_at) if artifact.created_at else None,
        updated_at=str(artifact.updated_at) if artifact.updated_at else None,
    )

@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: str, db: Session = Depends(get_db)):
    """下载成果物文件"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()

    if not artifact:
        raise HTTPException(404, "Artifact not found")

    storage_path = artifact.storage_path
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(404, "File not found on disk")

    with open(storage_path, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{artifact.name}"'},
    )
