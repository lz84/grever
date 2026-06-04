"""
成果物更新与删除端点
从 artifacts.py 拆分
"""
import json
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from reins.common.database import get_db_manager
from .artifacts_models import ArtifactUpdate, ArtifactResponse
from .artifacts_helpers import _row_to_artifact

router = APIRouter()

@router.patch("/{artifact_id}", response_model=ArtifactResponse)
def update_artifact(artifact_id: str, req: ArtifactUpdate):
    """更新成果物信息"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT * FROM artifacts WHERE id = :id"
        ), {"id": artifact_id}).fetchone()

    if not row:
        raise HTTPException(404, "Artifact not found")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.tags is not None:
        updates["tags"] = json.dumps(req.tags, ensure_ascii=False)

    if updates:
        updates["id"] = artifact_id
        with engine.begin() as conn:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates if k != "id")
            conn.execute(text(f"UPDATE artifacts SET {set_clause} WHERE id = :id"), updates)

    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT * FROM artifacts WHERE id = :id"
        ), {"id": artifact_id}).fetchone()

    return ArtifactResponse(**_row_to_artifact(dict(row._mapping)))

@router.delete("/{artifact_id}")
def delete_artifact(artifact_id: str):
    """删除成果物"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT storage_path FROM artifacts WHERE id = :id"
        ), {"id": artifact_id}).fetchone()

    if not row:
        raise HTTPException(404, "Artifact not found")

    if row[0] and os.path.exists(row[0]):
        os.remove(row[0])

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM artifacts WHERE id = :id"), {"id": artifact_id})

    return {"success": True, "message": "Artifact deleted"}
