"""Knowledge Base CRUD API

GET/POST/PUT/DELETE /api/v1/knowledge
"""
import json
import time
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from reins.common.database import get_db
from models import KnowledgeEntry, IndustryPack

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


# === Request/Response Models ===

class KnowledgeCreate(BaseModel):
    id: Optional[str] = None
    pack_id: str
    name: str
    category: str = "general"
    content: Optional[str] = None
    file_path: Optional[str] = None
    version: str = "1.0.0"
    tags: List[str] = []


class KnowledgeUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    file_path: Optional[str] = None
    version: Optional[str] = None
    tags: Optional[List[str]] = None


class KnowledgeResponse(BaseModel):
    id: str
    pack_id: str
    name: str
    category: str
    content: Optional[str]
    file_path: Optional[str]
    version: str
    tags: List[str]
    created_at: int


# === Helpers ===

def _parse_tags(raw) -> List[str]:
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


def _build_response(entry: KnowledgeEntry) -> KnowledgeResponse:
    return KnowledgeResponse(
        id=entry.id,
        pack_id=entry.pack_id,
        name=entry.name,
        category=entry.category,
        content=entry.content,
        file_path=entry.file_path,
        version=entry.version,
        tags=_parse_tags(entry.tags),
        created_at=entry.created_at,
    )


# === CRUD Endpoints ===

@router.get("", response_model=dict)
async def list_knowledge(
    pack_id: Optional[str] = Query(None, description="Filter by pack_id"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name/content"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List knowledge entries with optional filters."""
    query = db.query(KnowledgeEntry)

    if pack_id:
        query = query.filter(KnowledgeEntry.pack_id == pack_id)
    if category:
        query = query.filter(KnowledgeEntry.category == category)
    if search:
        pattern = f"%{search}%"
        from sqlalchemy import or_
        query = query.filter(
            or_(
                KnowledgeEntry.name.ilike(pattern),
                KnowledgeEntry.content.ilike(pattern)
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    entries = query.order_by(KnowledgeEntry.created_at.desc()).limit(page_size).offset(offset).all()

    return {
        "items": [_build_response(e) for e in entries],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{entry_id}", response_model=KnowledgeResponse)
async def get_knowledge(entry_id: str, db: Session = Depends(get_db)):
    """Get a single knowledge entry by ID."""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Knowledge entry '{entry_id}' not found")
    return _build_response(entry)


@router.post("", status_code=201, response_model=KnowledgeResponse)
async def create_knowledge(data: KnowledgeCreate, db: Session = Depends(get_db)):
    """Create a new knowledge entry."""
    # Verify pack exists
    pack = db.query(IndustryPack).filter(IndustryPack.id == data.pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{data.pack_id}' not found")

    entry_id = data.id or f"kb-{uuid.uuid4().hex[:8]}"
    now = int(time.time())

    existing = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Knowledge entry '{entry_id}' already exists")

    entry = KnowledgeEntry(
        id=entry_id,
        pack_id=data.pack_id,
        name=data.name,
        category=data.category,
        content=data.content,
        file_path=data.file_path,
        version=data.version,
        tags=json.dumps(data.tags, ensure_ascii=False),
        created_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _build_response(entry)


@router.put("/{entry_id}", response_model=KnowledgeResponse)
async def update_knowledge(entry_id: str, data: KnowledgeUpdate, db: Session = Depends(get_db)):
    """Update an existing knowledge entry."""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Knowledge entry '{entry_id}' not found")

    if data.name is not None:
        entry.name = data.name
    if data.category is not None:
        entry.category = data.category
    if data.content is not None:
        entry.content = data.content
    if data.file_path is not None:
        entry.file_path = data.file_path
    if data.version is not None:
        entry.version = data.version
    if data.tags is not None:
        entry.tags = json.dumps(data.tags, ensure_ascii=False)

    db.commit()
    db.refresh(entry)
    return _build_response(entry)


@router.delete("/{entry_id}")
async def delete_knowledge(entry_id: str, db: Session = Depends(get_db)):
    """Delete a knowledge entry."""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Knowledge entry '{entry_id}' not found")
    db.delete(entry)
    db.commit()
    return {"success": True, "id": entry_id}
