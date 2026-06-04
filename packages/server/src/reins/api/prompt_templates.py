# -*- coding: utf-8 -*-
"""Sprint 111: Prompt Templates CRUD API"""
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/prompt-templates", tags=["prompt-templates"])


# --- Pydantic Models ---

class PromptTemplateCreate(BaseModel):
    name: str
    scope: str
    template: str
    variables: Optional[str] = None
    tags: Optional[str] = None
    pack_id: Optional[str] = None


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    scope: Optional[str] = None
    template: Optional[str] = None
    variables: Optional[str] = None
    tags: Optional[str] = None
    pack_id: Optional[str] = None


# --- CRUD Endpoints ---

@router.get("")
async def list_prompt_templates(
    pack_id: Optional[str] = Query(None, description="Filter by pack_id"),
    scope: Optional[str] = Query(None, description="Filter by scope"),
    db: Session = Depends(get_db),
):
    """List prompt templates with optional filters."""
    conditions = []
    params: dict = {}

    if pack_id:
        conditions.append("pack_id = :pack_id")
        params["pack_id"] = pack_id
    if scope:
        conditions.append("scope = :scope")
        params["scope"] = scope

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    sql = f"SELECT * FROM prompt_templates {where} ORDER BY created_at DESC"
    rows = db.execute(text(sql), params).fetchall()

    return [_row_to_dict(row) for row in rows]


@router.get("/by-pack/{pack_id}")
async def get_by_pack(pack_id: str, db: Session = Depends(get_db)):
    """Get all prompt templates for a specific pack."""
    sql = "SELECT * FROM prompt_templates WHERE pack_id = :pack_id ORDER BY created_at DESC"
    rows = db.execute(text(sql), {"pack_id": pack_id}).fetchall()
    return [_row_to_dict(row) for row in rows]


@router.get("/{template_id}")
async def get_prompt_template(template_id: str, db: Session = Depends(get_db)):
    """Get a single prompt template by ID."""
    row = db.execute(
        text("SELECT * FROM prompt_templates WHERE id = :id"),
        {"id": template_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Prompt template '{template_id}' not found")
    return _row_to_dict(row)


@router.post("", status_code=201)
async def create_prompt_template(data: PromptTemplateCreate, db: Session = Depends(get_db)):
    """Create a new prompt template."""
    now = int(time.time())
    template_id = str(uuid.uuid4())

    db.execute(
        text("""
            INSERT INTO prompt_templates (id, name, scope, template, variables, tags, pack_id, created_at, updated_at)
            VALUES (:id, :name, :scope, :template, :variables, :tags, :pack_id, :created_at, :updated_at)
        """),
        {
            "id": template_id,
            "name": data.name,
            "scope": data.scope,
            "template": data.template,
            "variables": data.variables,
            "tags": data.tags,
            "pack_id": data.pack_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.commit()

    return {"success": True, "id": template_id}


@router.put("/{template_id}")
async def update_prompt_template(template_id: str, data: PromptTemplateUpdate, db: Session = Depends(get_db)):
    """Update an existing prompt template."""
    row = db.execute(
        text("SELECT id FROM prompt_templates WHERE id = :id"),
        {"id": template_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Prompt template '{template_id}' not found")

    now = int(time.time())
    update_fields = []
    params: dict = {"id": template_id, "updated_at": now}

    for field in ["name", "scope", "template", "variables", "tags", "pack_id"]:
        value = getattr(data, field, None)
        if value is not None:
            update_fields.append(f"{field} = :{field}")
            params[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_sql = f"UPDATE prompt_templates SET {', '.join(update_fields)}, updated_at = :updated_at WHERE id = :id"
    db.execute(text(update_sql), params)
    db.commit()

    return {"success": True, "id": template_id}


@router.delete("/{template_id}", status_code=204)
async def delete_prompt_template(template_id: str, db: Session = Depends(get_db)):
    """Delete a prompt template."""
    row = db.execute(
        text("SELECT id FROM prompt_templates WHERE id = :id"),
        {"id": template_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Prompt template '{template_id}' not found")

    db.execute(text("DELETE FROM prompt_templates WHERE id = :id"), {"id": template_id})
    db.commit()


# --- Helpers ---

def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "scope": row[2],
        "template": row[3],
        "variables": row[4],
        "tags": row[5],
        "pack_id": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }
