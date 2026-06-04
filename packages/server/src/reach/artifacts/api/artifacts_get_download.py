"""
成果物获取与下载端点
从 artifacts.py 拆分
"""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import text

from reins.common.database import get_db_manager
from .artifacts_models import ArtifactResponse
from .artifacts_helpers import _row_to_artifact

router = APIRouter()

@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: str):
    """获取成果物详情"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT * FROM artifacts WHERE id = :id"
        ), {"id": artifact_id}).fetchone()

    if not row:
        raise HTTPException(404, "Artifact not found")

    return ArtifactResponse(**_row_to_artifact(dict(row._mapping)))

@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: str):
    """下载成果物文件"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT name, storage_path FROM artifacts WHERE id = :id"
        ), {"id": artifact_id}).fetchone()

    if not row:
        raise HTTPException(404, "Artifact not found")

    storage_path = row[1]
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(404, "File not found on disk")

    with open(storage_path, "rb") as f:
        content = f.read()

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{row[0]}"'},
    )
