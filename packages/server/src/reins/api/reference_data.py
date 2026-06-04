# -*- coding: utf-8 -*-
"""Sprint 111: Reference Data CRUD API"""
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/reference-data", tags=["reference-data"])


# --- Pydantic Models ---

class ReferenceDataCreate(BaseModel):
    name: str
    type: str
    data: str
    tags: Optional[str] = None
    pack_id: Optional[str] = None


class ReferenceDataUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    data: Optional[str] = None
    tags: Optional[str] = None
    pack_id: Optional[str] = None


# --- CRUD Endpoints ---

@router.get("")
async def list_reference_data(
    type: Optional[str] = Query(None, description="Filter by type"),
    pack_id: Optional[str] = Query(None, description="Filter by pack_id"),
    db: Session = Depends(get_db),
):
    """List reference data with optional filters."""
    conditions = []
    params: dict = {}

    if type:
        conditions.append("type = :type")
        params["type"] = type
    if pack_id:
        conditions.append("pack_id = :pack_id")
        params["pack_id"] = pack_id

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    sql = f"SELECT * FROM reference_data {where} ORDER BY created_at DESC"
    rows = db.execute(text(sql), params).fetchall()

    return [_row_to_dict(row) for row in rows]


@router.get("/{ref_id}")
async def get_reference_data(ref_id: str, db: Session = Depends(get_db)):
    """Get a single reference data entry by ID."""
    row = db.execute(
        text("SELECT * FROM reference_data WHERE id = :id"),
        {"id": ref_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Reference data '{ref_id}' not found")
    return _row_to_dict(row)


@router.post("", status_code=201)
async def create_reference_data(data: ReferenceDataCreate, db: Session = Depends(get_db)):
    """Create a new reference data entry."""
    now = int(time.time())
    ref_id = str(uuid.uuid4())

    db.execute(
        text("""
            INSERT INTO reference_data (id, name, type, data, tags, pack_id, created_at, updated_at)
            VALUES (:id, :name, :type, :data, :tags, :pack_id, :created_at, :updated_at)
        """),
        {
            "id": ref_id,
            "name": data.name,
            "type": data.type,
            "data": data.data,
            "tags": data.tags,
            "pack_id": data.pack_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.commit()

    return {"success": True, "id": ref_id}


@router.put("/{ref_id}")
async def update_reference_data(ref_id: str, data: ReferenceDataUpdate, db: Session = Depends(get_db)):
    """Update an existing reference data entry."""
    row = db.execute(
        text("SELECT id FROM reference_data WHERE id = :id"),
        {"id": ref_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Reference data '{ref_id}' not found")

    now = int(time.time())
    update_fields = []
    params: dict = {"id": ref_id, "updated_at": now}

    for field in ["name", "type", "data", "tags", "pack_id"]:
        value = getattr(data, field, None)
        if value is not None:
            update_fields.append(f"{field} = :{field}")
            params[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_sql = f"UPDATE reference_data SET {', '.join(update_fields)}, updated_at = :updated_at WHERE id = :id"
    db.execute(text(update_sql), params)
    db.commit()

    return {"success": True, "id": ref_id}


@router.delete("/{ref_id}", status_code=204)
async def delete_reference_data(ref_id: str, db: Session = Depends(get_db)):
    """Delete a reference data entry."""
    row = db.execute(
        text("SELECT id FROM reference_data WHERE id = :id"),
        {"id": ref_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Reference data '{ref_id}' not found")

    db.execute(text("DELETE FROM reference_data WHERE id = :id"), {"id": ref_id})
    db.commit()


# --- Helpers ---

def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "type": row[2],
        "data": row[3],
        "tags": row[4],
        "pack_id": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }
