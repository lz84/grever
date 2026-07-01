"""Industry Packs CRUD API

Sprint 93: 行业能力标签库基础设施
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from reins.common.database import get_db
from models import IndustryPack
from reach.industry.api.industry_tag_models import (
    IndustryPackCreate,
    IndustryPackUpdate,
    IndustryPackResponse,
    IndustryPackDetailResponse,
    PackListResponse,
)

router = APIRouter(prefix="/api/v1/industry-packs", tags=["industry-packs"])


def _pack_row_to_response(row) -> IndustryPackResponse:
    """Convert a DB row to IndustryPackResponse."""
    return IndustryPackResponse(
        id=row[0],
        name=row[1],
        industry=row[2],
        version=row[3],
        description=row[4],
        tags_count=row[5] or 0,
        scenarios_count=row[6] or 0,
        skills_count=row[7] or 0,
        status=row[8],
        created_at=row[9],
        updated_at=row[10],
        pack_type=row[11] if len(row) > 11 else 'standard',
        base_pack_id=row[12] if len(row) > 12 else None,
    )


def _pack_model_to_response(pack: IndustryPack) -> IndustryPackResponse:
    """Convert a IndustryPack ORM model to IndustryPackResponse."""
    return IndustryPackResponse(
        id=pack.id,
        name=pack.name,
        industry=pack.industry,
        version=pack.version,
        description=pack.description or '',
        tags_count=pack.tags_count or 0,
        scenarios_count=pack.scenarios_count or 0,
        skills_count=pack.skills_count or 0,
        status=pack.status,
        created_at=pack.created_at,
        updated_at=pack.updated_at,
        pack_type=pack.pack_type if pack.pack_type else 'standard',
        base_pack_id=pack.base_pack_id,
    )


@router.get("")
async def list_packs(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List industry packs with pagination and filters."""
    query = db.query(IndustryPack)

    if industry:
        query = query.filter(IndustryPack.industry == industry)
    if status:
        query = query.filter(IndustryPack.status == status)

    total = query.count()

    offset = (page - 1) * page_size
    packs = query.order_by(IndustryPack.created_at.desc()).limit(page_size).offset(offset).all()

    items = []
    for p in packs:
        # Convert ORM model to tuple for _pack_row_to_response
        row = (
            p.id, p.name, p.industry, p.version, p.description,
            p.tags_count, p.scenarios_count, p.skills_count, p.status,
            p.created_at, p.updated_at,
            p.pack_type if p.pack_type else 'standard',
            p.base_pack_id,
        )
        items.append(_pack_row_to_response(row))

    return PackListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{pack_id}")
async def get_pack(pack_id: str, db: Session = Depends(get_db)):
    """Get a single pack by ID with its contents."""
    pack = db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()

    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    row = (
        pack.id, pack.name, pack.industry, pack.version, pack.description,
        pack.tags_count or 0, pack.scenarios_count or 0, pack.skills_count or 0,
        pack.status, pack.created_at, pack.updated_at,
        pack.pack_type if pack.pack_type else 'standard', pack.base_pack_id,
    )

    return IndustryPackDetailResponse(
        id=row[0],
        name=row[1],
        industry=row[2],
        version=row[3],
        description=row[4],
        tags_count=row[5] or 0,
        scenarios_count=row[6] or 0,
        skills_count=row[7] or 0,
        status=row[8],
        created_at=row[9],
        updated_at=row[10],
        pack_type=row[11],
        base_pack_id=row[12],
    )


@router.post("", status_code=201)
async def create_pack(data: IndustryPackCreate, db: Session = Depends(get_db)):
    """Create a new industry pack."""
    now = int(time.time())

    existing = db.query(IndustryPack).filter(IndustryPack.id == data.id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Pack '{data.id}' already exists")

    try:
        new_pack = IndustryPack(
            id=data.id,
            name=data.name,
            industry=data.industry,
            version=data.version,
            description=data.description,
            tags_count=0,
            scenarios_count=0,
            skills_count=0,
            status=data.status or "draft",
            created_at=now,
            updated_at=now,
            pack_type=getattr(data, 'pack_type', 'standard') or 'standard',
            base_pack_id=getattr(data, 'base_pack_id', None),
        )
        db.add(new_pack)
    except IntegrityError as e:
        db.rollback()
        err_msg = str(e.orig)
        if "custom_pack_requires_base" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="定制包必须指定 base_pack_id（基于哪个标准包）"
            )
        raise

    # db.commit() handled automatically by get_db dependency


@router.put("/{pack_id}")
async def update_pack(pack_id: str, data: IndustryPackUpdate, db: Session = Depends(get_db)):
    """Update an existing pack."""
    now = int(time.time())

    pack = db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    update_fields = {}

    for field in ['name', 'version', 'description', 'status', 'tags_count', 'scenarios_count', 'skills_count',
                   'pack_type', 'base_pack_id']:
        value = getattr(data, field, None)
        if value is not None:
            update_fields[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_fields["updated_at"] = now

    for key, value in update_fields.items():
        setattr(pack, key, value)

    # db.commit() handled automatically by get_db dependency

    return {"success": True, "id": pack_id}


@router.delete("/{pack_id}")
async def delete_pack(pack_id: str, db: Session = Depends(get_db)):
    """Delete a pack and its contents."""
    pack = db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    # Delete pack (related skills/knowledge/schemes have cascade='all, delete-orphan')
    db.delete(pack)
    # db.commit() handled automatically by get_db dependency

    return {"success": True, "id": pack_id}
