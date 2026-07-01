"""GRASP cognition CRUD endpoints — split from grasp_router.py"""

import json
import uuid
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query

from grasp.api.grasp_helpers import _load_cognitions, _save_cognitions

router = APIRouter()

_DANGEROUS_PATTERNS = [
    r'\b(?:execute|system|eval|exec)\s*\(',
    r'<script[^>]*>',
    r'--\s*drop\s+table',
    r'\.\./\.\.\.',
]

def _check_dangerous(content: str):
    """检测危险内容"""
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="检测到危险内容模式，已被拒绝",
            )

@router.get("/cognitions")
def list_cognitions(
    type: Optional[str] = Query(None, description="按类型过滤（fact/pattern/lesson/meta）"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    domain: Optional[str] = Query(None, description="按领域过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """列出所有认知（支持分页和过滤）。"""
    cognitions = _load_cognitions()
    if type:
        cognitions = [c for c in cognitions if c.get("type") == type]
    if status:
        cognitions = [c for c in cognitions if c.get("status") == status]
    if domain:
        cognitions = [c for c in cognitions if c.get("domain") == domain]
    total = len(cognitions)
    items = sorted(cognitions, key=lambda c: c.get("created_at", ""), reverse=True)[skip:skip + limit]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/cognition/{cognition_id}")
def get_cognition(cognition_id: str):
    """读取单个认知：根据 cognition_id 获取完整认知详情。"""
    cognitions = _load_cognitions()
    for c in cognitions:
        if c.get("cognition_id") == cognition_id:
            return {"status": "success", "cognition": c}
    raise HTTPException(status_code=404, detail=f"认知 {cognition_id} 不存在")

@router.post("/cognition")
async def create_cognition(request: Request):
    """写入认知：注入新认知到知识库。"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体必须是合法 JSON")

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="认知内容不能为空")

    cognition_type = body.get("type", "fact")
    if cognition_type not in ("fact", "pattern", "lesson", "meta"):
        raise HTTPException(status_code=400, detail="认知类型必须是 fact/pattern/lesson/meta 之一")

    confidence = body.get("confidence", 0.8)
    if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
        raise HTTPException(status_code=400, detail="置信度必须是 0-1 之间的数字")

    source = body.get("source", {})
    if not isinstance(source, dict):
        raise HTTPException(status_code=400, detail="source 必须是对象")

    tags = body.get("tags", [])
    if not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags 必须是数组")

    _check_dangerous(content)

    issues = []
    quality_score = 1.0
    if len(content) < 10:
        issues.append("content_too_short")
        quality_score -= 0.3
    if len(content) > 10000:
        issues.append("content_too_long")
        quality_score -= 0.2
    if confidence < 0.3:
        issues.append("low_confidence")
        quality_score -= 0.3
    quality_score = max(0, quality_score)

    now = datetime.now(timezone.utc)
    cognition_id = f"cog-{int(now.timestamp() * 1000)}-{uuid.uuid4().hex[:8]}"
    status = "published" if quality_score > 0.5 else "pending_review"

    cognition = {
        "cognition_id": cognition_id,
        "type": cognition_type,
        "content": content,
        "tags": tags,
        "confidence": confidence,
        "quality_score": round(quality_score, 2),
        "source": {
            "agent_id": source.get("agent_id", "unknown"),
            "task_id": source.get("task_id", ""),
            "channel": source.get("channel", "api"),
        },
        "status": status,
        "domain": body.get("domain", ""),
        "metadata": body.get("metadata", {}),
        "version": 1,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    cognitions = _load_cognitions()
    cognitions.append(cognition)
    _save_cognitions(cognitions)

    return {"status": "success", "cognition_id": cognition_id, "cognition": cognition}

@router.patch("/cognition/{cognition_id}")
async def update_cognition(cognition_id: str, request: Request):
    """修改认知：更新已有认知的字段。"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体必须是合法 JSON")

    if not body:
        raise HTTPException(status_code=400, detail="至少需要一个要更新的字段")

    cognitions = _load_cognitions()
    target = None
    target_idx = None
    for i, c in enumerate(cognitions):
        if c.get("cognition_id") == cognition_id:
            target = c
            target_idx = i
            break

    if target is None:
        raise HTTPException(status_code=404, detail=f"认知 {cognition_id} 不存在")

    new_content = body.get("content")
    if new_content is not None:
        new_content = new_content.strip()
        if not new_content:
            raise HTTPException(status_code=400, detail="认知内容不能为空")
        _check_dangerous(new_content)
        target["content"] = new_content

    if "type" in body:
        if body["type"] not in ("fact", "pattern", "lesson", "meta"):
            raise HTTPException(status_code=400, detail="认知类型必须是 fact/pattern/lesson/meta 之一")
        target["type"] = body["type"]

    if "tags" in body:
        if not isinstance(body["tags"], list):
            raise HTTPException(status_code=400, detail="tags 必须是数组")
        target["tags"] = body["tags"]

    if "confidence" in body:
        conf = body["confidence"]
        if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
            raise HTTPException(status_code=400, detail="置信度必须是 0-1 之间的数字")
        target["confidence"] = conf

    if "status" in body:
        if body["status"] not in ("published", "pending_review", "rejected"):
            raise HTTPException(status_code=400, detail="状态必须是 published/pending_review/rejected 之一")
        target["status"] = body["status"]

    if "domain" in body:
        target["domain"] = body["domain"]

    if "metadata" in body:
        if not isinstance(body["metadata"], dict):
            raise HTTPException(status_code=400, detail="metadata 必须是对象")
        if "metadata" not in target:
            target["metadata"] = {}
        target["metadata"].update(body["metadata"])

    target["version"] = target.get("version", 1) + 1
    target["updated_at"] = datetime.now(timezone.utc).isoformat()

    cognitions[target_idx] = target
    _save_cognitions(cognitions)

    return {"status": "success", "cognition_id": cognition_id, "cognition": target}

@router.delete("/cognition/{cognition_id}")
def delete_cognition(cognition_id: str):
    """删除认知：从知识库中移除指定认知。"""
    cognitions = _load_cognitions()
    new_cognitions = [c for c in cognitions if c.get("cognition_id") != cognition_id]

    if len(new_cognitions) == len(cognitions):
        raise HTTPException(status_code=404, detail=f"认知 {cognition_id} 不存在")

    _save_cognitions(new_cognitions)

    return {"status": "success", "message": f"认知 {cognition_id} 已删除"}
