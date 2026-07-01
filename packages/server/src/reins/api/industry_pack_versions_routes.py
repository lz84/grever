"""Industry Pack Versions, Upgrade, and Diff API

Sprint 112: 版本管理 + 包对比
"""
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import IndustryPack, IndustryPackVersion

router = APIRouter(prefix="/api/v1/industry-packs", tags=["industry-pack-versions"])


# ─────────────────────────────────────────────────────────
# B112-1: GET /{pack_id}/versions — 版本历史
# ─────────────────────────────────────────────────────────

@router.get("/{pack_id}/versions")
async def list_pack_versions(
    pack_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """返回包的版本历史列表（支持分页）。"""
    # Verify pack exists
    pack = db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    # Count versions
    total = db.query(IndustryPackVersion).filter(
        IndustryPackVersion.pack_id == pack_id
    ).count()

    offset = (page - 1) * page_size
    rows = db.query(IndustryPackVersion).filter(
        IndustryPackVersion.pack_id == pack_id
    ).order_by(
        IndustryPackVersion.created_at.desc(),
        IndustryPackVersion.id.desc(),
    ).offset(offset).limit(page_size).all()

    items = []
    for row in rows:
        item = {
            "id": row.id,
            "pack_id": row.pack_id,
            "version": row.version,
            "action": row.action,
            "source_file": row.source_file,
            "source_checksum": row.source_checksum,
            "imported_at": row.imported_at,
            "notes": row.notes,
            "created_at": row.created_at,
            "stats": row.to_dict()["stats"] if hasattr(row, 'to_dict') else None,
        }
        items.append(item)

    return {
        "pack_id": pack_id,
        "versions": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─────────────────────────────────────────────────────────
# B112-2: POST /{pack_id}/upgrade — 升级包到新版本
# ─────────────────────────────────────────────────────────

@router.post("/{pack_id}/upgrade")
async def upgrade_pack(
    pack_id: str,
    body: dict,
    db: Session = Depends(get_db),
):
    """升级包到新版本。

    请求体:
    {
        "new_version": "1.1.0",
        "notes": "Optional notes about this upgrade",
        "changes": {
            "added": [{"content_type": "tag", "content_id": "new:tag-id"}, ...],
            "modified": [{"content_type": "tag", "content_id": "existing:tag-id"}, ...],
            "removed": [{"content_type": "tag", "content_id": "old:tag-id"}, ...]
        }
    }

    行为:
    - 新增内容插入 industry_pack_contents
    - 删除内容标记 deprecated（添加一个 _deprecated: 前缀的条目）
    - 记录版本历史到 industry_pack_versions
    - 更新包的版本号
    """
    # Verify pack exists
    pack = db.query(IndustryPack).filter(IndustryPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    new_version = body.get("new_version")
    if not new_version:
        raise HTTPException(status_code=400, detail="new_version is required")

    old_version = pack.version
    changes = body.get("changes", {})
    notes = body.get("notes", f"Upgraded from {old_version} to {new_version}")
    now = int(time.time())

    added = changes.get("added", [])
    modified = changes.get("modified", [])
    removed = changes.get("removed", [])

    # Note: industry_pack_contents is removed. Content tracking now relies on pack_id FKs in business tables.
    # We still count the changes provided in the request for version history purposes.
    added_count = len(added)
    modified_count = len(modified)
    removed_count = len(removed)

    # --- Update pack version ---
    pack.version = new_version
    pack.updated_at = now

    # --- Record version history ---
    stats = json.dumps({
        "added": added_count,
        "modified": modified_count,
        "removed": removed_count,
    })
    version_id = f"ipv-{pack_id}-{new_version}"
    # Make unique if this version already exists
    existing_ver = db.query(IndustryPackVersion).filter(
        IndustryPackVersion.pack_id == pack_id,
        IndustryPackVersion.version == new_version,
    ).first()
    if existing_ver:
        version_id = f"{version_id}-{uuid.uuid4().hex[:6]}"

    db.add(IndustryPackVersion(
        id=version_id,
        pack_id=pack_id,
        version=new_version,
        action='upgrade',
        stats=stats,
        imported_at=now,
        notes=notes,
        created_at=now,
    ))

    db.commit()

    return {
        "success": True,
        "pack_id": pack_id,
        "old_version": old_version,
        "new_version": new_version,
        "changes": {
            "added": added_count,
            "modified": modified_count,
            "removed": removed_count,
        },
        "version_record_id": version_id,
    }


# ─────────────────────────────────────────────────────────
# B112-3: GET /{pack_a}/diff/{pack_b} — 包对比
# ─────────────────────────────────────────────────────────

@router.get("/{pack_a}/diff/{pack_b}")
async def diff_packs(
    pack_a: str,
    pack_b: str,
    db: Session = Depends(get_db),
):
    """对比两个包的内容差异。

    返回 added/modified/removed 的内容列表。
    added = 在 pack_b 中存在但 pack_a 中不存在
    removed = 在 pack_a 中存在但 pack_b 中不存在
    modified = 在两个包中都存在但状态不同（deprecated 标记变化）
    """
    # Verify both packs exist
    for pid in [pack_a, pack_b]:
        pack = db.query(IndustryPack).filter(IndustryPack.id == pid).first()
        if not pack:
            raise HTTPException(status_code=404, detail=f"Pack '{pid}' not found")

    # Get contents of both packs by querying business tables directly
    from models import Skill, KnowledgeEntry, AgentScheme

    def get_pack_contents(pid):
        skills = db.query(Skill.id, Skill.pack_id).filter(Skill.pack_id == pid).all()
        knowledge = db.query(KnowledgeEntry.id, KnowledgeEntry.pack_id).filter(KnowledgeEntry.pack_id == pid).all()
        agents = db.query(AgentScheme.id, AgentScheme.pack_id).filter(AgentScheme.pack_id == pid).all()
        
        contents = set()
        for sid, _ in skills:
            contents.add(("skill", sid))
        for kid, _ in knowledge:
            contents.add(("knowledge", kid))
        for aid, _ in agents:
            contents.add(("agent_scheme", aid))
        return contents

    contents_a = get_pack_contents(pack_a)
    contents_b = get_pack_contents(pack_b)

    # Added in B (in B but not in A)
    added = [{"content_type": ct, "content_id": ci} for ct, ci in contents_b - contents_a]

    # Removed from A (in A but not in B)
    removed = [{"content_type": ct, "content_id": ci} for ct, ci in contents_a - contents_b]

    # Deprecated tracking removed along with industry_pack_contents table
    modified = []

    pack_a_ver = db.query(IndustryPack).with_entities(IndustryPack.version).filter(
        IndustryPack.id == pack_a
    ).first()
    pack_b_ver = db.query(IndustryPack).with_entities(IndustryPack.version).filter(
        IndustryPack.id == pack_b
    ).first()

    return {
        "pack_a": {
            "id": pack_a,
            "version": pack_a_ver[0] if pack_a_ver else None,
        },
        "pack_b": {
            "id": pack_b,
            "version": pack_b_ver[0] if pack_b_ver else None,
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
        },
    }