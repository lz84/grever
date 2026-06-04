# -*- coding: utf-8 -*-
"""Sprint 86e-1: Context API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Literal

from reins.common.database import get_db
from models.task import Task
from models.project import Project
from models.goal import Goal

router = APIRouter(prefix="/api/v1/context", tags=["context"])

_ENTITY_MAP = {
    "tasks": Task,
    "projects": Project,
    "goals": Goal,
}

class ContextGetResponse(BaseModel):
    entity: str
    entity_id: str
    context_md: str | None

class ContextUpdateRequest(BaseModel):
    context_md: str

class ContextUpdateResponse(BaseModel):
    success: bool
    entity: str
    entity_id: str
    context_md: str

@router.get("/{entity}/{entity_id}", response_model=ContextGetResponse)
def get_context(
    entity: Literal["tasks", "projects", "goals"],
    entity_id: str,
    db: Session = Depends(get_db),
) -> ContextGetResponse:
    model = _ENTITY_MAP.get(entity)
    if not model:
        raise HTTPException(status_code=400, detail="Unknown entity: " + entity)
    row = db.query(model).filter(model.id == entity_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=entity.rstrip("s") + " " + entity_id + " not found")
    return ContextGetResponse(
        entity=entity,
        entity_id=entity_id,
        context_md=getattr(row, "context_md", None),
    )

@router.put("/{entity}/{entity_id}", response_model=ContextUpdateResponse)
def update_context(
    entity: Literal["tasks", "projects", "goals"],
    entity_id: str,
    body: ContextUpdateRequest,
    db: Session = Depends(get_db),
) -> ContextUpdateResponse:
    model = _ENTITY_MAP.get(entity)
    if not model:
        raise HTTPException(status_code=400, detail="Unknown entity: " + entity)
    row = db.query(model).filter(model.id == entity_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=entity.rstrip("s") + " " + entity_id + " not found")
    row.context_md = body.context_md
    db.commit()
    return ContextUpdateResponse(
        success=True,
        entity=entity,
        entity_id=entity_id,
        context_md=body.context_md,
    )