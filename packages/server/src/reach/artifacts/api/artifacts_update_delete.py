"""
成果物更新与删除端点
从 artifacts.py 拆分
"""
import json
import os

from fastapi import APIRouter, HTTPException

from models.artifact import Artifact
from .artifacts_models import ArtifactUpdate, ArtifactResponse
from .artifacts_helpers import _row_to_artifact
from reins.common.database import get_db_manager

router = APIRouter()

@router.patch("/{artifact_id}", response_model=ArtifactResponse)
def update_artifact(artifact_id: str, req: ArtifactUpdate):
    """更新成果物信息"""
    db = get_db_manager().get_session()
    try:
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(404, "Artifact not found")

        if req.name is not None:
            artifact.name = req.name
        if req.description is not None:
            artifact.description = req.description
        if req.tags is not None:
            artifact.tags = json.dumps(req.tags, ensure_ascii=False)

        db.commit()

        row = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        return ArtifactResponse(**_row_to_artifact({
            "id": row.id, "name": row.name, "description": row.description,
            "storage_path": row.storage_path, "mime_type": row.mime_type,
            "file_size": row.file_size, "sha256_hash": row.sha256_hash,
            "tags": row.tags, "created_by": row.created_by,
            "created_at": row.created_at, "updated_at": row.updated_at,
        }))
    finally:
        db.close()

@router.delete("/{artifact_id}")
def delete_artifact(artifact_id: str):
    """删除成果物"""
    db = get_db_manager().get_session()
    try:
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise HTTPException(404, "Artifact not found")

        if artifact.storage_path and os.path.exists(artifact.storage_path):
            os.remove(artifact.storage_path)

        db.delete(artifact)
        db.commit()
        return {"success": True, "message": "Artifact deleted"}
    finally:
        db.close()
