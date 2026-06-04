# -*- coding: utf-8 -*-
"""Sprint 111: SOPs CRUD API"""
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/sops", tags=["sops"])


# --- Pydantic Models ---

class SopCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    content: str
    version: Optional[str] = None
    tags: Optional[str] = None
    related_tasks: Optional[str] = None
    pack_id: Optional[str] = None


class SopUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    content: Optional[str] = None
    version: Optional[str] = None
    tags: Optional[str] = None
    related_tasks: Optional[str] = None
    pack_id: Optional[str] = None


# --- CRUD Endpoints ---

@router.get("")
async def list_sops(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    pack_id: Optional[str] = Query(None, description="Filter by pack_id"),
    db: Session = Depends(get_db),
):
    """List SOPs with optional filters."""
    conditions = []
    params: dict = {}

    if industry:
        conditions.append("industry = :industry")
        params["industry"] = industry
    if pack_id:
        conditions.append("pack_id = :pack_id")
        params["pack_id"] = pack_id

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    sql = f"SELECT * FROM sops {where} ORDER BY created_at DESC"
    rows = db.execute(text(sql), params).fetchall()

    return [_row_to_dict(row) for row in rows]


@router.get("/{sop_id}")
async def get_sop(sop_id: str, db: Session = Depends(get_db)):
    """Get a single SOP by ID."""
    row = db.execute(
        text("SELECT * FROM sops WHERE id = :id"),
        {"id": sop_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"SOP '{sop_id}' not found")
    return _row_to_dict(row)


@router.post("", status_code=201)
async def create_sop(data: SopCreate, db: Session = Depends(get_db)):
    """Create a new SOP."""
    now = int(time.time())
    sop_id = str(uuid.uuid4())

    db.execute(
        text("""
            INSERT INTO sops (id, name, industry, content, version, tags, related_tasks, pack_id, created_at, updated_at)
            VALUES (:id, :name, :industry, :content, :version, :tags, :related_tasks, :pack_id, :created_at, :updated_at)
        """),
        {
            "id": sop_id,
            "name": data.name,
            "industry": data.industry,
            "content": data.content,
            "version": data.version,
            "tags": data.tags,
            "related_tasks": data.related_tasks,
            "pack_id": data.pack_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.commit()

    return {"success": True, "id": sop_id}


@router.put("/{sop_id}")
async def update_sop(sop_id: str, data: SopUpdate, db: Session = Depends(get_db)):
    """Update an existing SOP."""
    row = db.execute(
        text("SELECT id FROM sops WHERE id = :id"),
        {"id": sop_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"SOP '{sop_id}' not found")

    now = int(time.time())
    update_fields = []
    params: dict = {"id": sop_id, "updated_at": now}

    for field in ["name", "industry", "content", "version", "tags", "related_tasks", "pack_id"]:
        value = getattr(data, field, None)
        if value is not None:
            update_fields.append(f"{field} = :{field}")
            params[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_sql = f"UPDATE sops SET {', '.join(update_fields)}, updated_at = :updated_at WHERE id = :id"
    db.execute(text(update_sql), params)
    db.commit()

    return {"success": True, "id": sop_id}


@router.delete("/{sop_id}", status_code=204)
async def delete_sop(sop_id: str, db: Session = Depends(get_db)):
    """Delete a SOP."""
    row = db.execute(
        text("SELECT id FROM sops WHERE id = :id"),
        {"id": sop_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"SOP '{sop_id}' not found")

    db.execute(text("DELETE FROM sops WHERE id = :id"), {"id": sop_id})
    db.commit()


# --- Helpers ---

def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "industry": row[2],
        "content": row[3],
        "version": row[4],
        "tags": row[5],
        "related_tasks": row[6],
        "pack_id": row[7],
        "created_at": row[8],
        "updated_at": row[9],
    }
