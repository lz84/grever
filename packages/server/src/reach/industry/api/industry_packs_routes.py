"""Industry Packs CRUD API

Sprint 93: 行业能力标签库基础设施
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from reins.common.database import get_db
from reach.industry.api.industry_tag_models import (
    IndustryPackCreate,
    IndustryPackUpdate,
    IndustryPackResponse,
    IndustryPackDetailResponse,
    IndustryPackContentItem,
    PackListResponse,
)

router = APIRouter(prefix="/api/v1/industry-packs", tags=["industry-packs"])

@router.get("")
async def list_packs(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List industry packs with pagination and filters."""
    conditions = []
    params = {}

    if industry:
        conditions.append("industry = :industry")
        params["industry"] = industry
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    # Count
    count_sql = f"SELECT COUNT(*) FROM industry_packs {where}"
    total = db.execute(text(count_sql), params).scalar()

    # Data
    offset = (page - 1) * page_size
    data_sql = f"SELECT * FROM industry_packs {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = offset
    rows = db.execute(text(data_sql), params).fetchall()

    items = [_pack_row_to_response(row) for row in rows]
    return PackListResponse(items=items, total=total, page=page, page_size=page_size)

@router.get("/{pack_id}")
async def get_pack(pack_id: str, db: Session = Depends(get_db)):
    """Get a single pack by ID with its contents."""
    row = db.execute(
        text("SELECT * FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    # Get contents
    content_rows = db.execute(
        text("SELECT pack_id, content_type, content_id FROM industry_pack_contents WHERE pack_id = :pack_id"),
        {"pack_id": pack_id}
    ).fetchall()

    contents = [
        IndustryPackContentItem(
            pack_id=r[0],
            content_type=r[1],
            content_id=r[2],
        )
        for r in content_rows
    ]

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
        pack_type=row[11] if len(row) > 11 else 'standard',
        base_pack_id=row[12] if len(row) > 12 else None,
        contents=contents,
    )

@router.post("", status_code=201)
async def create_pack(data: IndustryPackCreate, db: Session = Depends(get_db)):
    """Create a new industry pack."""
    now = int(time.time())

    existing = db.execute(
        text("SELECT id FROM industry_packs WHERE id = :id"),
        {"id": data.id}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Pack '{data.id}' already exists")

    try:
        db.execute(
            text("""
                INSERT INTO industry_packs 
                (id, name, industry, version, description, tags_count, scenarios_count, 
                 skills_count, status, created_at, updated_at, pack_type, base_pack_id)
                VALUES (:id, :name, :industry, :version, :description, 0, 0, 0, 
                        :status, :created_at, :updated_at, :pack_type, :base_pack_id)
            """),
            {
                "id": data.id,
                "name": data.name,
                "industry": data.industry,
                "version": data.version,
                "description": data.description,
                "status": data.status or "draft",
                "created_at": now,
                "updated_at": now,
                "pack_type": getattr(data, 'pack_type', 'standard') or 'standard',
                "base_pack_id": getattr(data, 'base_pack_id', None),
            }
        )
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Extract TRIGGER error message (SQLite constraint errors)
        err_msg = str(e.orig)
        if "custom_pack_requires_base" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="定制包必须指定 base_pack_id（基于哪个标准包）"
            )
        raise

    return {"success": True, "id": data.id}

@router.put("/{pack_id}")
async def update_pack(pack_id: str, data: IndustryPackUpdate, db: Session = Depends(get_db)):
    """Update an existing pack."""
    now = int(time.time())

    existing = db.execute(
        text("SELECT id FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    update_fields = []
    params = {"id": pack_id, "updated_at": now}

    for field in ['name', 'version', 'description', 'status', 'tags_count', 'scenarios_count', 'skills_count',
                   'pack_type', 'base_pack_id']:
        value = getattr(data, field, None)
        if value is not None:
            update_fields.append(f"{field} = :{field}")
            params[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_sql = f"UPDATE industry_packs SET {', '.join(update_fields)}, updated_at = :updated_at WHERE id = :id"
    db.execute(text(update_sql), params)
    db.commit()

    return {"success": True, "id": pack_id}

@router.delete("/{pack_id}")
async def delete_pack(pack_id: str, db: Session = Depends(get_db)):
    """Delete a pack and its contents."""
    existing = db.execute(
        text("SELECT id FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    # Delete contents first
    db.execute(
        text("DELETE FROM industry_pack_contents WHERE pack_id = :pack_id"),
        {"pack_id": pack_id}
    )
    # Delete pack
    db.execute(
        text("DELETE FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    )
    db.commit()

    return {"success": True, "id": pack_id}

@router.post("/{pack_id}/contents", status_code=201)
async def add_content(pack_id: str, data: IndustryPackContentItem, db: Session = Depends(get_db)):
    """Add a content association to a pack."""
    existing = db.execute(
        text("SELECT id FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    db.execute(
        text("""
            INSERT OR IGNORE INTO industry_pack_contents (pack_id, content_type, content_id)
            VALUES (:pack_id, :content_type, :content_id)
        """),
        {
            "pack_id": data.pack_id,
            "content_type": data.content_type,
            "content_id": data.content_id,
        }
    )
    db.commit()

    return {"success": True}

@router.delete("/{pack_id}/contents/{content_type}/{content_id}")
async def remove_content(pack_id: str, content_type: str, content_id: str, db: Session = Depends(get_db)):
    """Remove a content association from a pack."""
    from urllib.parse import unquote
    content_id = unquote(content_id)

    db.execute(
        text("DELETE FROM industry_pack_contents WHERE pack_id = :pack_id AND content_type = :content_type AND content_id = :content_id"),
        {"pack_id": pack_id, "content_type": content_type, "content_id": content_id}
    )
    db.commit()

    return {"success": True}

# ============ Helpers ============

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
