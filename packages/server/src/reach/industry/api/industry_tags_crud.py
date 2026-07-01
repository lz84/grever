"""
行业标签 CRUD
"""
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models.industry_tag import IndustryCapabilityTag

router = APIRouter(prefix="/api/v1/industry-tags")


def _serialize(obj):
    if obj is None:
        return None
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False)
    return obj


def _deserialize(data):
    if data is None:
        return None
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return data
    return data


def _build_tag_response(tag):
    return {
        "id": tag.id,
        "name": getattr(tag, 'tag_name', '') or '',
        "tag_name_en": getattr(tag, 'tag_name_en', '') or '',
        "description": tag.description or '',
        "industry": tag.industry,
        "dimension": getattr(tag, 'dimension', '') or '',
        "level": getattr(tag, 'level', '') or '',
        "category": getattr(tag, 'category', 'custom') or 'custom',
        "status": tag.status or 'active',
        "prerequisites": _deserialize(getattr(tag, 'prerequisites', None)),
        "tools": _deserialize(getattr(tag, 'tools', None)),
        "examples": _deserialize(getattr(tag, 'examples', None)),
        "created_at": tag.created_at,
        "updated_at": tag.updated_at,
    }


def list_tags(db: Session, industry: str = None, category: str = None, search: str = None):
    query = db.query(IndustryCapabilityTag)
    if industry:
        query = query.filter(IndustryCapabilityTag.industry == industry)
    if category:
        query = query.filter(IndustryCapabilityTag.dimension == category)
    if search:
        pattern = f"%{search}%"
        from sqlalchemy import or_
        query = query.filter(
            or_(
                IndustryCapabilityTag.tag_name.ilike(pattern),
                IndustryCapabilityTag.description.ilike(pattern)
            )
        )
    return query.order_by(IndustryCapabilityTag.industry.asc(), IndustryCapabilityTag.tag_name.asc()).all()


def get_tag_by_id(db: Session, tag_id: str):
    return db.query(IndustryCapabilityTag).filter(IndustryCapabilityTag.id == tag_id).first()


def create_tag(db: Session, tag_data):
    new_tag = IndustryCapabilityTag(
        id=tag_data["id"],
        tag_name=tag_data["name"],
        tag_name_en=tag_data.get("tag_name_en"),
        description=tag_data.get("description", ""),
        industry=tag_data["industry"],
        dimension=tag_data.get("dimension", tag_data.get("category", "custom")),
        level=tag_data.get("level", "basic"),
        prerequisites=_serialize(tag_data.get("prerequisites")),
        tools=_serialize(tag_data.get("tools")),
        examples=_serialize(tag_data.get("examples")),
        status=tag_data.get("status", "active"),
        created_at=tag_data.get("created_at", 0),
        updated_at=tag_data.get("updated_at"),
    )
    db.add(new_tag)
    db.commit()
    return new_tag


def update_tag(db: Session, tag_id: str, tag_data):
    tag = db.query(IndustryCapabilityTag).filter(IndustryCapabilityTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag.tag_name = tag_data.get("name", tag.tag_name)
    tag.description = tag_data.get("description", tag.description)
    tag.industry = tag_data.get("industry", tag.industry)
    tag.dimension = tag_data.get("dimension", tag_data.get("category", tag.dimension))
    tag.level = tag_data.get("level", tag.level)
    if "prerequisites" in tag_data:
        tag.prerequisites = _serialize(tag_data["prerequisites"])
    if "tools" in tag_data:
        tag.tools = _serialize(tag_data["tools"])
    if "examples" in tag_data:
        tag.examples = _serialize(tag_data["examples"])
    tag.status = tag_data.get("status", tag.status)
    tag.updated_at = tag_data.get("updated_at", tag.updated_at)
    db.commit()
    return tag


def delete_tag(db: Session, tag_id: str):
    tag = db.query(IndustryCapabilityTag).filter(IndustryCapabilityTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
    return {"success": True}
