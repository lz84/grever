"""
成果物创建与列表端点
从 artifacts.py 拆分
"""
import base64
import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from reins.common.database import get_db_manager
from .artifacts_models import ArtifactCreate, ArtifactResponse, ArtifactListResponse
from .artifacts_helpers import _row_to_artifact
from typing import Optional

router = APIRouter()

ARTIFACTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "data", "artifacts"
)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

@router.post("/", response_model=ArtifactResponse)
def create_artifact(req: ArtifactCreate):
    """上传成果物（MVP: 文件存本地，元数据存 DB）"""
    artifact_id = f"art-{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    storage_path = None
    file_size = 0
    file_url = None

    if req.content_base64:
        try:
            file_bytes = base64.b64decode(req.content_base64)
            file_size = len(file_bytes)

            ext = ""
            if req.type == "image":
                ext = ".png"
            elif req.type == "document":
                ext = ".txt"
            elif req.type == "code":
                ext = ".py"
            elif req.type == "data":
                ext = ".json"

            filename = f"{artifact_id}_{req.name}"
            storage_path = os.path.join(ARTIFACTS_DIR, filename)

            with open(storage_path, "wb") as f:
                f.write(file_bytes)

            file_url = f"/api/v1/artifacts/{artifact_id}/download"
        except Exception as e:
            raise HTTPException(400, f"文件解码失败: {str(e)}")

    tags_json = json.dumps(req.tags, ensure_ascii=False) if req.tags else None

    engine = get_db_manager().engine
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO artifacts
            (id, task_id, project_id, goal_id, created_by, name, type,
             storage_path, url, size, description, tags, created_at)
            VALUES (:id, :task_id, :project_id, :goal_id, :created_by, :name, :type,
                    :storage_path, :url, :size, :desc, :tags, :now)
        """), {
            "id": artifact_id,
            "task_id": req.task_id,
            "project_id": req.project_id,
            "goal_id": req.goal_id,
            "created_by": req.created_by,
            "name": req.name,
            "type": req.type,
            "storage_path": storage_path,
            "url": file_url,
            "size": file_size,
            "desc": req.description,
            "tags": tags_json,
            "now": now,
        })

    return ArtifactResponse(
        id=artifact_id,
        task_id=req.task_id,
        project_id=req.project_id,
        goal_id=req.goal_id,
        created_by=req.created_by,
        name=req.name,
        type=req.type,
        url=file_url,
        size=file_size,
        description=req.description,
        tags=req.tags or [],
        created_at=now,
    )

@router.get("/", response_model=ArtifactListResponse)
def list_artifacts(
    task_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    goal_id: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """列出成果物"""
    engine = get_db_manager().engine

    conditions = []
    params = {"limit": limit, "offset": offset}

    if task_id:
        conditions.append("task_id = :task_id")
        params["task_id"] = task_id
    if project_id:
        conditions.append("project_id = :project_id")
        params["project_id"] = project_id
    if goal_id:
        conditions.append("goal_id = :goal_id")
        params["goal_id"] = goal_id
    if created_by:
        conditions.append("created_by = :created_by")
        params["created_by"] = created_by
    if type:
        conditions.append("type = :type")
        params["type"] = type

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    with engine.connect() as conn:
        count_row = conn.execute(text(
            f"SELECT count(*) FROM artifacts WHERE {where_clause}"
        ), params).fetchone()
        total = count_row[0]

        rows = conn.execute(text(f"""
            SELECT * FROM artifacts
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

    items = [_row_to_artifact(dict(r._mapping)) for r in rows]
    return ArtifactListResponse(artifacts=items, total=total)
