"""Agent Scheme CRUD API

GET/POST/PUT/DELETE /api/v1/agent-schemes
"""
import json
import time
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from reins.common.database import get_db
from models import AgentScheme, AgentSchemeRole, IndustryPack

router = APIRouter(prefix="/api/v1/agent-schemes", tags=["agent-schemes"])


# === Request/Response Models ===

class AgentSchemeCreate(BaseModel):
    id: Optional[str] = None
    pack_id: str
    name: str
    description: Optional[str] = None
    roles: Optional[List[dict]] = []


class AgentSchemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AgentSchemeRoleCreate(BaseModel):
    id: Optional[str] = None
    role_name: str
    required_tags: List[str] = []
    priority: int = 0


class AgentSchemeResponse(BaseModel):
    id: str
    pack_id: str
    name: str
    description: Optional[str]
    roles: List[dict]
    created_at: int


# === Helpers ===

def _parse_roles(raw):
    if isinstance(raw, list):
        return raw
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _build_response(scheme: AgentScheme) -> AgentSchemeResponse:
    roles = _parse_roles(getattr(scheme, 'roles', None))
    return AgentSchemeResponse(
        id=scheme.id,
        pack_id=scheme.pack_id,
        name=scheme.name,
        description=scheme.description,
        roles=roles,
        created_at=scheme.created_at,
    )


# === CRUD Endpoints ===

@router.get("", response_model=dict)
async def list_schemes(
    pack_id: Optional[str] = Query(None, description="Filter by pack_id"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List agent schemes with optional pack_id filter."""
    query = db.query(AgentScheme)
    if pack_id:
        query = query.filter(AgentScheme.pack_id == pack_id)

    total = query.count()
    offset = (page - 1) * page_size
    schemes = query.order_by(AgentScheme.created_at.desc()).limit(page_size).offset(offset).all()

    return {
        "items": [_build_response(s) for s in schemes],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{scheme_id}", response_model=AgentSchemeResponse)
async def get_scheme(scheme_id: str, db: Session = Depends(get_db)):
    """Get a single agent scheme by ID."""
    scheme = db.query(AgentScheme).filter(AgentScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Agent scheme '{scheme_id}' not found")
    return _build_response(scheme)


@router.post("", status_code=201, response_model=AgentSchemeResponse)
async def create_scheme(data: AgentSchemeCreate, db: Session = Depends(get_db)):
    """Create a new agent scheme (optionally with roles)."""
    # Verify pack exists
    pack = db.query(IndustryPack).filter(IndustryPack.id == data.pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{data.pack_id}' not found")

    scheme_id = data.id or f"scheme-{uuid.uuid4().hex[:8]}"
    existing = db.query(AgentScheme).filter(AgentScheme.id == scheme_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent scheme '{scheme_id}' already exists")

    now = int(time.time())
    scheme = AgentScheme(
        id=scheme_id,
        pack_id=data.pack_id,
        name=data.name,
        description=data.description,
        roles=json.dumps(data.roles or [], ensure_ascii=False),
        created_at=now,
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return _build_response(scheme)


@router.put("/{scheme_id}", response_model=AgentSchemeResponse)
async def update_scheme(scheme_id: str, data: AgentSchemeUpdate, db: Session = Depends(get_db)):
    """Update an existing agent scheme."""
    scheme = db.query(AgentScheme).filter(AgentScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Agent scheme '{scheme_id}' not found")

    if data.name is not None:
        scheme.name = data.name
    if data.description is not None:
        scheme.description = data.description

    db.commit()
    db.refresh(scheme)
    return _build_response(scheme)


@router.delete("/{scheme_id}")
async def delete_scheme(scheme_id: str, db: Session = Depends(get_db)):
    """Delete an agent scheme and its roles (CASCADE)."""
    scheme = db.query(AgentScheme).filter(AgentScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Agent scheme '{scheme_id}' not found")
    db.delete(scheme)
    db.commit()
    return {"success": True, "id": scheme_id}


# === Role sub-resources ===

@router.get("/{scheme_id}/roles", response_model=dict)
async def list_roles(scheme_id: str, db: Session = Depends(get_db)):
    """List roles for a scheme."""
    scheme = db.query(AgentScheme).filter(AgentScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Agent scheme '{scheme_id}' not found")

    roles = db.query(AgentSchemeRole).filter(AgentSchemeRole.scheme_id == scheme_id).order_by(
        AgentSchemeRole.priority.desc()
    ).all()

    return {
        "items": [
            {
                "id": r.id,
                "scheme_id": r.scheme_id,
                "role_name": r.role_name,
                "required_tags": _parse_roles(r.required_tags),
                "priority": r.priority,
            }
            for r in roles
        ],
        "total": len(roles),
    }


@router.post("/{scheme_id}/roles", status_code=201, response_model=dict)
async def create_role(scheme_id: str, data: AgentSchemeRoleCreate, db: Session = Depends(get_db)):
    """Add a role to a scheme."""
    scheme = db.query(AgentScheme).filter(AgentScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Agent scheme '{scheme_id}' not found")

    role_id = data.id or f"role-{uuid.uuid4().hex[:8]}"
    existing = db.query(AgentSchemeRole).filter(AgentSchemeRole.id == role_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Role '{role_id}' already exists")

    role = AgentSchemeRole(
        id=role_id,
        scheme_id=scheme_id,
        role_name=data.role_name,
        required_tags=json.dumps(data.required_tags or [], ensure_ascii=False),
        priority=data.priority,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return {
        "id": role.id,
        "scheme_id": role.scheme_id,
        "role_name": role.role_name,
        "required_tags": _parse_roles(role.required_tags),
        "priority": role.priority,
    }


@router.delete("/{scheme_id}/roles/{role_id}")
async def delete_role(scheme_id: str, role_id: str, db: Session = Depends(get_db)):
    """Delete a role from a scheme."""
    role = db.query(AgentSchemeRole).filter(
        AgentSchemeRole.id == role_id,
        AgentSchemeRole.scheme_id == scheme_id,
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found in scheme '{scheme_id}'")
    db.delete(role)
    db.commit()
    return {"success": True, "id": role_id}
