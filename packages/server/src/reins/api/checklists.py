# -*- coding: utf-8 -*-
"""Sprint 111: Checklists CRUD API"""
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/checklists", tags=["checklists"])


# --- Pydantic Models ---

class ChecklistCreate(BaseModel):
    name: str
    scope: str
    items: str
    tags: Optional[str] = None
    related_tasks: Optional[str] = None
    pack_id: Optional[str] = None


class ChecklistUpdate(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    items: Optional[str] = None
    tags: Optional[str] = None
    related_tasks: Optional[str] = None
    pack_id: Optional[str] = None


# --- CRUD Endpoints ---

@router.get("")
async def list_checklists(
    scope: Optional[str] = Query(None, description="Filter by scope"),
    pack_id: Optional[str] = Query(None, description="Filter by pack_id"),
    db: Session = Depends(get_db),
):
    """List checklists with optional filters."""
    conditions = []
    params: dict = {}

    if scope:
        conditions.append("scope = :scope")
        params["scope"] = scope
    if pack_id:
        conditions.append("pack_id = :pack_id")
        params["pack_id"] = pack_id

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    sql = f"SELECT * FROM checklists {where} ORDER BY created_at DESC"
    rows = db.execute(text(sql), params).fetchall()

    return [_row_to_dict(row) for row in rows]


@router.get("/{checklist_id}")
async def get_checklist(checklist_id: str, db: Session = Depends(get_db)):
    """Get a single checklist by ID."""
    row = db.execute(
        text("SELECT * FROM checklists WHERE id = :id"),
        {"id": checklist_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Checklist '{checklist_id}' not found")
    return _row_to_dict(row)


@router.post("", status_code=201)
async def create_checklist(data: ChecklistCreate, db: Session = Depends(get_db)):
    """Create a new checklist."""
    now = int(time.time())
    checklist_id = str(uuid.uuid4())

    db.execute(
        text("""
            INSERT INTO checklists (id, name, scope, items, tags, related_tasks, pack_id, created_at, updated_at)
            VALUES (:id, :name, :scope, :items, :tags, :related_tasks, :pack_id, :created_at, :updated_at)
        """),
        {
            "id": checklist_id,
            "name": data.name,
            "scope": data.scope,
            "items": data.items,
            "tags": data.tags,
            "related_tasks": data.related_tasks,
            "pack_id": data.pack_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.commit()

    return {"success": True, "id": checklist_id}


@router.put("/{checklist_id}")
async def update_checklist(checklist_id: str, data: ChecklistUpdate, db: Session = Depends(get_db)):
    """Update an existing checklist."""
    row = db.execute(
        text("SELECT id FROM checklists WHERE id = :id"),
        {"id": checklist_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Checklist '{checklist_id}' not found")

    now = int(time.time())
    update_fields = []
    params: dict = {"id": checklist_id, "updated_at": now}

    for field in ["name", "scope", "items", "tags", "related_tasks", "pack_id"]:
        value = getattr(data, field, None)
        if value is not None:
            update_fields.append(f"{field} = :{field}")
            params[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_sql = f"UPDATE checklists SET {', '.join(update_fields)}, updated_at = :updated_at WHERE id = :id"
    db.execute(text(update_sql), params)
    db.commit()

    return {"success": True, "id": checklist_id}


@router.delete("/{checklist_id}", status_code=204)
async def delete_checklist(checklist_id: str, db: Session = Depends(get_db)):
    """Delete a checklist."""
    row = db.execute(
        text("SELECT id FROM checklists WHERE id = :id"),
        {"id": checklist_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Checklist '{checklist_id}' not found")

    db.execute(text("DELETE FROM checklists WHERE id = :id"), {"id": checklist_id})
    db.commit()


# --- Helpers ---

def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "scope": row[2],
        "items": row[3],
        "tags": row[4],
        "related_tasks": row[5],
        "pack_id": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }
