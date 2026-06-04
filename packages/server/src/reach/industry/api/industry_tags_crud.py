"""Industry Capability Tags — CRUD endpoints."""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db
from reach.industry.api.industry_tag_models import (
    IndustryCapabilityTagCreate, IndustryCapabilityTagUpdate,
)
from .industry_tags_helpers import (
    _row_to_response, _to_json, _parse_json_safe, _count_tag_references, compute_version_change,
)

router = APIRouter(prefix="/api/v1/industry-tags", tags=["industry-tags"])


@router.get("")
async def list_tags(
    industry: Optional[str] = Query(None), dimension: Optional[str] = Query(None),
    level: Optional[str] = Query(None), status: Optional[str] = Query(None),
    search: Optional[str] = Query(None), page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
):
    """List industry capability tags with pagination and filters."""
    conditions, params = [], {}
    if industry: conditions.append("industry = :industry"); params["industry"] = industry
    if dimension: conditions.append("dimension = :dimension"); params["dimension"] = dimension
    if level: conditions.append("level = :level"); params["level"] = level
    if status: conditions.append("status = :status"); params["status"] = status
    if search: conditions.append("(tag_name LIKE :search OR description LIKE :search OR id LIKE :search)"); params["search"] = f"%{search}%"
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM industry_capability_tags {where}"), params).scalar()
    offset = (page - 1) * page_size
    params["limit"], params["offset"] = page_size, offset
    rows = db.execute(text(f"SELECT * FROM industry_capability_tags {where} ORDER BY id LIMIT :limit OFFSET :offset"), params).fetchall()
    from .industry_tags_helpers import TagListResponse
    return TagListResponse(items=[_row_to_response(row) for row in rows], total=total, page=page, page_size=page_size)


@router.get("/{tag_id}")
async def get_tag(tag_id: str, db: Session = Depends(get_db)):
    """Get a single tag by ID."""
    row = db.execute(text("SELECT * FROM industry_capability_tags WHERE id = :id"), {"id": tag_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found")
    return _row_to_response(row)


@router.post("", status_code=201)
async def create_tag(data: IndustryCapabilityTagCreate, db: Session = Depends(get_db)):
    """Create a new industry capability tag."""
    now = int(time.time())
    existing = db.execute(text("SELECT id FROM industry_capability_tags WHERE id = :id"), {"id": data.id}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Tag '{data.id}' already exists")
    db.execute(text("""
        INSERT INTO industry_capability_tags 
        (id, industry, tag_name, tag_name_en, description, dimension, level, 
         prerequisites, tools, examples, status, created_at, updated_at)
        VALUES (:id, :industry, :tag_name, :tag_name_en, :description, :dimension, 
                :level, :prerequisites, :tools, :examples, :status, :created_at, :updated_at)
    """), {"id": data.id, "industry": data.industry, "tag_name": data.tag_name,
        "tag_name_en": data.tag_name_en, "description": data.description,
        "dimension": data.dimension, "level": data.level,
        "prerequisites": _to_json(data.prerequisites), "tools": _to_json(data.tools),
        "examples": _to_json(data.examples), "status": data.status or "active",
        "created_at": now, "updated_at": now})
    db.commit()
    return {"success": True, "id": data.id}


@router.put("/{tag_id}")
async def update_tag(tag_id: str, data: IndustryCapabilityTagUpdate, db: Session = Depends(get_db)):
    """Update an existing tag."""
    now = int(time.time())
    existing = db.execute(text("SELECT id, status FROM industry_capability_tags WHERE id = :id"), {"id": tag_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found")

    if data.replaced_by is not None:
        target_row = db.execute(text("SELECT id, status FROM industry_capability_tags WHERE id = :id"), {"id": data.replaced_by}).fetchone()
        if not target_row:
            raise HTTPException(status_code=400, detail=f"replaced_by target '{data.replaced_by}' does not exist")
        if target_row[1] == "deprecated":
            raise HTTPException(status_code=400, detail=f"replaced_by target '{data.replaced_by}' is already deprecated")

    warning = None
    new_status = getattr(data, 'status', None)
    if new_status == "deprecated":
        refs = _count_tag_references(tag_id, db)
        if refs["total_count"] > 0:
            warning = {"message": f"Tag is referenced by {refs['total_count']} object(s).", "references": refs}

    if data.replaced_by is not None and (new_status is None or new_status == "active"):
        new_status = "replaced_by"

    update_fields, params = [], {"id": tag_id, "updated_at": now}
    for field in ['tag_name', 'tag_name_en', 'description', 'dimension', 'level']:
        value = getattr(data, field, None)
        if value is not None: update_fields.append(f"{field} = :{field}"); params[field] = value
    if data.replaced_by is not None: update_fields.append("replaced_by = :replaced_by"); params["replaced_by"] = data.replaced_by
    if new_status is not None: update_fields.append("status = :status"); params["status"] = new_status
    for json_field in ['prerequisites', 'tools', 'examples']:
        value = getattr(data, json_field, None)
        if value is not None: update_fields.append(f"{json_field} = :{json_field}"); params[json_field] = _to_json(value)

    old_tag_row = db.execute(text("SELECT id, tag_name, tag_name_en, description, dimension, prerequisites, tools, examples, status, version_major, version_minor, version_patch FROM industry_capability_tags WHERE id = :id"), {"id": tag_id}).fetchone()
    old_tag = {'id': old_tag_row[0], 'tag_name': old_tag_row[1], 'tag_name_en': old_tag_row[2],
        'description': old_tag_row[3], 'dimension': old_tag_row[4],
        'prerequisites': _parse_json_safe(old_tag_row[5]), 'tools': _parse_json_safe(old_tag_row[6]),
        'examples': _parse_json_safe(old_tag_row[7]), 'status': old_tag_row[8],
        'version_major': old_tag_row[9], 'version_minor': old_tag_row[10], 'version_patch': old_tag_row[11]}
    new_tag = {'id': data.id if hasattr(data, 'id') and data.id is not None else old_tag['id'],
        'tag_name': data.tag_name if data.tag_name is not None else old_tag['tag_name'],
        'tag_name_en': data.tag_name_en if data.tag_name_en is not None else old_tag['tag_name_en'],
        'description': data.description if data.description is not None else old_tag['description'],
        'dimension': data.dimension if data.dimension is not None else old_tag['dimension'],
        'prerequisites': getattr(data, 'prerequisites', None) or old_tag['prerequisites'],
        'tools': getattr(data, 'tools', None) or old_tag['tools'],
        'examples': getattr(data, 'examples', None) or old_tag['examples']}

    version_level = compute_version_change(old_tag, new_tag)
    auto_ver_major, auto_ver_minor, auto_ver_patch = old_tag['version_major'], old_tag['version_minor'], old_tag['version_patch']
    if version_level == "MAJOR": auto_ver_major += 1; auto_ver_minor = 0; auto_ver_patch = 0
    elif version_level == "MINOR": auto_ver_minor += 1; auto_ver_patch = 0
    elif version_level == "PATCH": auto_ver_patch += 1
    ver_major = data.version_major if data.version_major is not None else auto_ver_major
    ver_minor = data.version_minor if data.version_minor is not None else auto_ver_minor
    ver_patch = data.version_patch if data.version_patch is not None else auto_ver_patch

    for vfield, vval in [('version_major', ver_major), ('version_minor', ver_minor), ('version_patch', ver_patch)]:
        update_fields.append(f"{vfield} = :{vfield}"); params[vfield] = vval

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    db.execute(text(f"UPDATE industry_capability_tags SET {', '.join(update_fields)}, updated_at = :updated_at WHERE id = :id"), params)
    db.commit()
    result = {"success": True, "id": tag_id}
    if warning: result["warning"] = warning
    return result


@router.delete("/{tag_id}")
async def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    """Delete a tag: hard-delete if unreferenced, soft-delete otherwise."""
    now = int(time.time())
    existing = db.execute(text("SELECT id FROM industry_capability_tags WHERE id = :id"), {"id": tag_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found")
    refs = _count_tag_references(tag_id, db)
    if refs["total_count"] > 0:
        db.execute(text("UPDATE industry_capability_tags SET status = 'deprecated', updated_at = :updated_at WHERE id = :id"), {"id": tag_id, "updated_at": now})
        db.commit()
        return {"deleted": False, "soft_deleted": True, "message": f"Tag referenced by {refs['total_count']} object(s). Soft-deleted.", "references": refs}
    else:
        db.execute(text("DELETE FROM industry_capability_tags WHERE id = :id"), {"id": tag_id})
        db.commit()
        return {"deleted": True, "soft_deleted": False, "message": "Tag deleted permanently."}


@router.get("/{tag_id}/references")
async def get_tag_references(tag_id: str, db: Session = Depends(get_db)):
    """Return reference statistics for a tag."""
    existing = db.execute(text("SELECT id FROM industry_capability_tags WHERE id = :id"), {"id": tag_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found")
    refs = _count_tag_references(tag_id, db)
    refs["tag_id"] = tag_id
    return refs
