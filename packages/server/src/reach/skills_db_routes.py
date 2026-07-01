"""
Industry Pack Skills DB API

CRUD + pack_id filter for skills stored in the `skills` table.
Existing `reach/skills.py` handles file-based Grever built-in skills;
this router handles DB-backed industry pack skills.
"""
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import Skill, IndustryPack

router = APIRouter(prefix="/api/v1/pack-skills", tags=["pack-skills"])


class SkillCreate(BaseModel):
    id: Optional[str] = None
    pack_id: str
    name: str
    description: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    required_tags: Optional[list[str]] = None
    tool_dependency: Optional[str] = None


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    required_tags: Optional[list[str]] = None
    tool_dependency: Optional[str] = None


class SkillResponse:
    def __init__(self, skill: Skill):
        self.id = skill.id
        self.pack_id = skill.pack_id
        self.name = skill.name
        self.description = skill.description
        self.input_schema = skill.input_schema
        self.output_schema = skill.output_schema
        self.required_tags = skill.required_tags
        self.tool_dependency = skill.tool_dependency
        self.created_at = skill.created_at
        self.updated_at = skill.updated_at


@router.get("")
def list_skills(
    pack_id: Optional[str] = Query(None, description="Filter by industry pack ID"),
    db: Session = Depends(get_db),
):
    """List skills, optionally filtered by pack_id."""
    query = db.query(Skill)

    if pack_id:
        query = query.filter(Skill.pack_id == pack_id)

    skills = query.order_by(Skill.created_at.desc()).all()

    return {
        "skills": [
            {
                "id": s.id,
                "pack_id": s.pack_id,
                "name": s.name,
                "description": s.description,
                "input_schema": s.input_schema,
                "output_schema": s.output_schema,
                "required_tags": s.required_tags,
                "tool_dependency": s.tool_dependency,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@router.get("/{skill_id}")
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    """Get a single skill by ID."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    return {
        "id": skill.id,
        "pack_id": skill.pack_id,
        "name": skill.name,
        "description": skill.description,
        "input_schema": skill.input_schema,
        "output_schema": skill.output_schema,
        "required_tags": skill.required_tags,
        "tool_dependency": skill.tool_dependency,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
    }


@router.get("/by-pack/{pack_id}")
def list_skills_by_pack(pack_id: str, db: Session = Depends(get_db)):
    """List all skills belonging to a specific industry pack."""
    skills = (
        db.query(Skill)
        .filter(Skill.pack_id == pack_id)
        .order_by(Skill.name)
        .all()
    )

    return {
        "pack_id": pack_id,
        "skills": [
            {
                "id": s.id,
                "pack_id": s.pack_id,
                "name": s.name,
                "description": s.description,
                "input_schema": s.input_schema,
                "output_schema": s.output_schema,
                "required_tags": s.required_tags,
                "tool_dependency": s.tool_dependency,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in skills
        ],
        "total": len(skills),
    }


def _skill_to_dict(skill: Skill) -> dict:
    """Convert a Skill ORM object to dict."""
    return {
        "id": skill.id,
        "pack_id": skill.pack_id,
        "name": skill.name,
        "description": skill.description,
        "input_schema": skill.input_schema,
        "output_schema": skill.output_schema,
        "required_tags": skill.required_tags,
        "tool_dependency": skill.tool_dependency,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
    }


@router.post("", status_code=201)
def create_skill(data: SkillCreate, db: Session = Depends(get_db)):
    """Create a new pack skill."""
    # Verify pack exists
    pack = db.query(IndustryPack).filter(IndustryPack.id == data.pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{data.pack_id}' not found")

    skill_id = data.id or f"skill-{int(time.time())}-{hash(data.name) % 10000:04d}"
    now = int(time.time())

    existing = db.query(Skill).filter(Skill.id == skill_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Skill '{skill_id}' already exists")

    skill = Skill(
        id=skill_id,
        pack_id=data.pack_id,
        name=data.name,
        description=data.description or "",
        input_schema=json.dumps(data.input_schema or {}),
        output_schema=json.dumps(data.output_schema or {}),
        required_tags=json.dumps(data.required_tags or []),
        tool_dependency=data.tool_dependency,
        created_at=now,
        updated_at=now,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


@router.put("/{skill_id}")
def update_skill(skill_id: str, data: SkillUpdate, db: Session = Depends(get_db)):
    """Update an existing pack skill."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    if data.name is not None:
        skill.name = data.name
    if data.description is not None:
        skill.description = data.description
    if data.input_schema is not None:
        skill.input_schema = json.dumps(data.input_schema)
    if data.output_schema is not None:
        skill.output_schema = json.dumps(data.output_schema)
    if data.required_tags is not None:
        skill.required_tags = json.dumps(data.required_tags)
    if data.tool_dependency is not None:
        skill.tool_dependency = data.tool_dependency

    skill.updated_at = int(time.time())
    db.commit()
    db.refresh(skill)
    return _skill_to_dict(skill)


@router.delete("/{skill_id}")
def delete_skill(skill_id: str, db: Session = Depends(get_db)):
    """Delete a pack skill."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    db.delete(skill)
    db.commit()
    return {"success": True, "id": skill_id}
