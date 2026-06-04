"""Industry Pack Versions, Upgrade, and Diff API

Sprint 112: 版本管理 + 包对比
"""
import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

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
    pack = db.execute(
        text("SELECT id FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    ).fetchone()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    # Count versions
    total = db.execute(
        text("SELECT COUNT(*) FROM industry_pack_versions WHERE pack_id = :pack_id"),
        {"pack_id": pack_id}
    ).scalar()

    offset = (page - 1) * page_size
    rows = db.execute(
        text("""
            SELECT id, pack_id, version, action, source_file, source_checksum,
                   stats, imported_at, notes, created_at
            FROM industry_pack_versions
            WHERE pack_id = :pack_id
            ORDER BY created_at DESC, id DESC
            LIMIT :limit OFFSET :offset
        """),
        {"pack_id": pack_id, "limit": page_size, "offset": offset}
    ).fetchall()

    items = []
    for row in rows:
        item = {
            "id": row[0],
            "pack_id": row[1],
            "version": row[2],
            "action": row[3],
            "source_file": row[4],
            "source_checksum": row[5],
            "imported_at": row[7],
            "notes": row[8],
            "created_at": row[9],
        }
        # Parse stats JSON if present
        if row[6]:
            try:
                item["stats"] = json.loads(row[6])
            except (json.JSONDecodeError, TypeError):
                item["stats"] = row[6]
        else:
            item["stats"] = None
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
    pack = db.execute(
        text("SELECT * FROM industry_packs WHERE id = :id"),
        {"id": pack_id}
    ).fetchone()
    if not pack:
        raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found")

    new_version = body.get("new_version")
    if not new_version:
        raise HTTPException(status_code=400, detail="new_version is required")

    old_version = pack[3]  # version column
    changes = body.get("changes", {})
    notes = body.get("notes", f"Upgraded from {old_version} to {new_version}")
    now = int(time.time())

    added = changes.get("added", [])
    modified = changes.get("modified", [])
    removed = changes.get("removed", [])

    added_count = 0
    modified_count = 0
    removed_count = 0

    # --- Added: insert new contents ---
    for item in added:
        content_type = item.get("content_type")
        content_id = item.get("content_id")
        if not content_type or not content_id:
            continue
        # Skip if already exists
        existing = db.execute(
            text("SELECT 1 FROM industry_pack_contents WHERE pack_id = :pack_id AND content_type = :ct AND content_id = :ci"),
            {"pack_id": pack_id, "ct": content_type, "ci": content_id}
        ).fetchone()
        if not existing:
            db.execute(
                text("INSERT INTO industry_pack_contents (pack_id, content_type, content_id) VALUES (:pack_id, :ct, :ci)"),
                {"pack_id": pack_id, "ct": content_type, "ci": content_id}
            )
            added_count += 1

    # --- Modified: just count (content_id already exists) ---
    for item in modified:
        content_type = item.get("content_type")
        content_id = item.get("content_id")
        if not content_type or not content_id:
            continue
        existing = db.execute(
            text("SELECT 1 FROM industry_pack_contents WHERE pack_id = :pack_id AND content_type = :ct AND content_id = :ci"),
            {"pack_id": pack_id, "ct": content_type, "ci": content_id}
        ).fetchone()
        if existing:
            modified_count += 1
        else:
            # Treat as added if it doesn't exist yet
            db.execute(
                text("INSERT INTO industry_pack_contents (pack_id, content_type, content_id) VALUES (:pack_id, :ct, :ci)"),
                {"pack_id": pack_id, "ct": content_type, "ci": content_id}
            )
            modified_count += 1

    # --- Removed: mark deprecated (add _deprecated entry, don't physically delete) ---
    for item in removed:
        content_type = item.get("content_type")
        content_id = item.get("content_id")
        if not content_type or not content_id:
            continue
        # Mark as deprecated by inserting a _deprecated prefixed entry
        deprecated_id = f"_deprecated:{content_id}"
        db.execute(
            text("""
                INSERT OR REPLACE INTO industry_pack_contents (pack_id, content_type, content_id)
                VALUES (:pack_id, :ct, :ci)
            """),
            {"pack_id": pack_id, "ct": f"_deprecated:{content_type}", "ci": content_id}
        )
        removed_count += 1

    # --- Update pack version ---
    db.execute(
        text("UPDATE industry_packs SET version = :version, updated_at = :now WHERE id = :id"),
        {"version": new_version, "now": now, "id": pack_id}
    )

    # --- Record version history ---
    stats = json.dumps({
        "added": added_count,
        "modified": modified_count,
        "removed": removed_count,
    })
    version_id = f"ipv-{pack_id}-{new_version}"
    # Make unique if this version already exists
    existing_ver = db.execute(
        text("SELECT id FROM industry_pack_versions WHERE pack_id = :pack_id AND version = :version"),
        {"pack_id": pack_id, "version": new_version}
    ).fetchone()
    if existing_ver:
        version_id = f"{version_id}-{uuid.uuid4().hex[:6]}"

    db.execute(
        text("""
            INSERT INTO industry_pack_versions
            (id, pack_id, version, action, stats, imported_at, notes, created_at)
            VALUES (:id, :pack_id, :version, 'upgrade', :stats, :now, :notes, :now)
        """),
        {
            "id": version_id,
            "pack_id": pack_id,
            "version": new_version,
            "stats": stats,
            "now": now,
            "notes": notes,
        }
    )

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
        pack = db.execute(
            text("SELECT id, name, version FROM industry_packs WHERE id = :id"),
            {"id": pid}
        ).fetchone()
        if not pack:
            raise HTTPException(status_code=404, detail=f"Pack '{pid}' not found")

    # Get contents of both packs
    rows_a = db.execute(
        text("SELECT content_type, content_id FROM industry_pack_contents WHERE pack_id = :pack_id"),
        {"pack_id": pack_a}
    ).fetchall()

    rows_b = db.execute(
        text("SELECT content_type, content_id FROM industry_pack_contents WHERE pack_id = :pack_id"),
        {"pack_id": pack_b}
    ).fetchall()

    contents_a = {(r[0], r[1]) for r in rows_a}
    contents_b = {(r[0], r[1]) for r in rows_b}

    # Added in B (in B but not in A)
    added = []
    for ct, ci in contents_b - contents_a:
        # Skip deprecated markers as "removed"
        if not ct.startswith("_deprecated:"):
            added.append({"content_type": ct, "content_id": ci})

    # Removed from A (in A but not in B)
    removed = []
    for ct, ci in contents_a - contents_b:
        if not ct.startswith("_deprecated:"):
            removed.append({"content_type": ct, "content_id": ci})

    # Modified: same content_id in both, but one has deprecated marker
    # Check for content that exists as normal in one and deprecated in other
    modified = []
    normal_a = {(ct, ci) for ct, ci in contents_a if not ct.startswith("_deprecated:")}
    deprecated_a = {(ct, ci) for ct, ci in contents_a if ct.startswith("_deprecated:")}
    normal_b = {(ct, ci) for ct, ci in contents_b if not ct.startswith("_deprecated:")}
    deprecated_b = {(ct, ci) for ct, ci in contents_b if ct.startswith("_deprecated:")}

    # Extract content_ids from deprecated entries
    dep_a_ids = {(ct.replace("_deprecated:", ""), ci) for ct, ci in deprecated_a}
    dep_b_ids = {(ct.replace("_deprecated:", ""), ci) for ct, ci in deprecated_b}

    # Deprecation status changed
    for ct, ci in normal_a & dep_b_ids:
        modified.append({
            "content_type": ct,
            "content_id": ci,
            "change": "deprecated_in_b",
        })
    for ct, ci in normal_b & dep_a_ids:
        modified.append({
            "content_type": ct,
            "content_id": ci,
            "change": "deprecated_in_a",
        })

    return {
        "pack_a": {
            "id": pack_a,
            "version": db.execute(
                text("SELECT version FROM industry_packs WHERE id = :id"),
                {"id": pack_a}
            ).fetchone()[0],
        },
        "pack_b": {
            "id": pack_b,
            "version": db.execute(
                text("SELECT version FROM industry_packs WHERE id = :id"),
                {"id": pack_b}
            ).fetchone()[0],
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
