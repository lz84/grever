"""
附件 API 路由 - Sprint 84 统一附件体系

提供完整的附件上传、下载、删除、关联管理功能。
"""

import os
import hashlib
import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Response, Body
from fastapi.responses import FileResponse
from sqlalchemy import text

from reins.common.database import get_db_session

router = APIRouter(prefix="/attachments", tags=["attachments"])

# 配置
ATTACHMENT_ROOT = os.environ.get("ATTACHMENT_ROOT", "data/attachments")
ATTACHMENT_MAX_SIZE = int(os.environ.get("ATTACHMENT_MAX_SIZE", 52428800))  # 50MB

# 文件类型黑名单
BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".scr", ".msi",
    ".js", ".vbs", ".ps1", ".wsf", ".hta",
    ".dll", ".sys", ".com", ".pif", ".lnk",
    ".jar", ".app", ".sh", ".bash",
}

# 合法的 entity_type
VALID_ENTITY_TYPES = {"goal", "project", "task", "scenario", "step", "agent"}

def _safe_filename(filename: str) -> str:
    filename = filename.replace("/", "_").replace("\\", "_").replace("..", "")
    for char in '<>:"|?*':
        filename = filename.replace(char, "_")
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    return filename

def _storage_path(attachment_id: str, filename: str) -> str:
    now = datetime.now()
    subdir = f"{now.strftime('%Y')}/{now.strftime('%m')}"
    root = ATTACHMENT_ROOT
    if not os.path.isabs(root):
        root = os.path.abspath(root)
    return os.path.join(root, subdir, f"{attachment_id}_{_safe_filename(filename)}")

def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def _check_entity_exists(entity_type: str, entity_id: str, db) -> bool:
    table_name = f"{entity_type}s"
    try:
        row = db.execute(text(
            f"SELECT 1 FROM {table_name} WHERE id = :eid LIMIT 1"
        ), {"eid": entity_id}).fetchone()
        return row is not None
    except Exception:
        return False

@router.post("/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    created_by: Optional[str] = Form(None),
):
    """上传附件"""
    db = get_db_session()
    try:
        if entity_type not in VALID_ENTITY_TYPES:
            raise HTTPException(400, {"code": "INVALID_ENTITY", "message": f"不支持的实体类型: {entity_type}"})

        content = await file.read()
        if len(content) > ATTACHMENT_MAX_SIZE:
            raise HTTPException(413, {"code": "FILE_TOO_LARGE", "message": "文件过大，最大支持 50MB"})

        _, ext = os.path.splitext(file.filename.lower())
        if ext in BLOCKED_EXTENSIONS:
            raise HTTPException(400, {"code": "FILE_TYPE_BLOCKED", "message": f"不支持的文件类型: {ext}"})

        if not _check_entity_exists(entity_type, entity_id, db):
            raise HTTPException(404, {"code": "ENTITY_NOT_FOUND", "message": f"实体不存在: {entity_type}/{entity_id}"})

        file_hash = _sha256(content)

        # 去重检查
        existing = db.execute(text(
            "SELECT id, filename, file_path, mime_type, file_size FROM attachments WHERE sha256_hash = :h"
        ), {"h": file_hash}).fetchone()

        if existing:
            attachment_id = existing[0]
            reused = True
            mime_type = existing[3]
        else:
            attachment_id = f"att-{uuid.uuid4().hex[:8]}"
            file_path = _storage_path(attachment_id, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)

            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
            db.execute(text("""
                INSERT INTO attachments (id, filename, file_path, mime_type, sha256_hash, file_size, created_by, created_at)
                VALUES (:id, :fn, :fp, :mt, :h, :sz, :cb, :ca)
            """), {
                "id": attachment_id, "fn": file.filename, "fp": file_path,
                "mt": mime_type, "h": file_hash, "sz": len(content),
                "cb": created_by, "ca": datetime.now().isoformat(),
            })
            reused = False

        # 创建 link
        db.execute(text("""
            INSERT INTO attachment_links (id, attachment_id, entity_type, entity_id, created_by, created_at)
            VALUES (:id, :aid, :et, :eid, :cb, :ca)
        """), {
            "id": f"link-{uuid.uuid4().hex[:8]}", "aid": attachment_id,
            "et": entity_type, "eid": entity_id, "cb": created_by,
            "ca": datetime.now().isoformat(),
        })
        db.commit()

        return {
            "success": True, "attachment_id": attachment_id, "reused": reused,
            "filename": file.filename, "file_size": len(content), "mime_type": mime_type,
        }
    finally:
        db.close()

@router.get("/{id}/download")
async def download_attachment(id: str, download: bool = Query(False)):
    """下载附件"""
    db = get_db_session()
    try:
        att = db.execute(text(
            "SELECT filename, file_path, mime_type FROM attachments WHERE id = :id"
        ), {"id": id}).fetchone()

        if not att:
            raise HTTPException(404, "附件不存在")

        filename, file_path, mime_type = att
        if not os.path.exists(file_path):
            raise HTTPException(404, "文件不存在")

        safe_name = Path(file_path).name.split("_", 1)[1] if "_" in Path(file_path).name else filename
        headers = {"Content-Disposition": f'attachment; filename="{safe_name}"'} if download else {}
        return FileResponse(file_path, filename=safe_name, media_type=mime_type or "application/octet-stream", headers=headers)
    finally:
        db.close()

@router.delete("/{id}")
async def delete_attachment(id: str, force: bool = Query(False)):
    """删除附件"""
    db = get_db_session()
    try:
        att = db.execute(text(
            "SELECT file_path FROM attachments WHERE id = :id"
        ), {"id": id}).fetchone()

        if not att:
            raise HTTPException(404, "附件不存在")

        link_count = db.execute(text(
            "SELECT COUNT(*) FROM attachment_links WHERE attachment_id = :id"
        ), {"id": id}).fetchone()[0]

        if link_count > 0 and not force:
            raise HTTPException(409, {
                "code": "ATTACHMENT_IN_USE",
                "message": f"此附件还被 {link_count} 个实体关联",
                "hint": "使用 ?force=true 强制删除"
            })

        db.execute(text("DELETE FROM attachment_links WHERE attachment_id = :id"), {"id": id})
        if os.path.exists(att[0]):
            os.remove(att[0])
        db.execute(text("DELETE FROM attachments WHERE id = :id"), {"id": id})
        db.commit()
        return {"success": True}
    finally:
        db.close()

@router.post("/{id}/link")
async def link_attachment(id: str, link_data: dict = Body(...)):
    """关联附件到实体"""
    db = get_db_session()
    try:
        if not db.execute(text("SELECT 1 FROM attachments WHERE id = :id"), {"id": id}).fetchone():
            raise HTTPException(404, "附件不存在")

        entity_type = link_data.get("entity_type")
        entity_id = link_data.get("entity_id")
        if not entity_type or not entity_id:
            raise HTTPException(400, "缺少 entity_type 或 entity_id")
        if entity_type not in VALID_ENTITY_TYPES:
            raise HTTPException(400, {"code": "INVALID_ENTITY", "message": f"不支持的实体类型: {entity_type}"})

        if not _check_entity_exists(entity_type, entity_id, db):
            raise HTTPException(404, {"code": "ENTITY_NOT_FOUND", "message": f"实体不存在"})

        if db.execute(text(
            "SELECT 1 FROM attachment_links WHERE attachment_id = :aid AND entity_type = :et AND entity_id = :eid"
        ), {"aid": id, "et": entity_type, "eid": entity_id}).fetchone():
            return {"success": True, "message": "已关联"}

        db.execute(text("""
            INSERT INTO attachment_links (id, attachment_id, entity_type, entity_id, created_by, created_at)
            VALUES (:id, :aid, :et, :eid, :cb, :ca)
        """), {
            "id": f"link-{uuid.uuid4().hex[:8]}", "aid": id,
            "et": entity_type, "eid": entity_id, "cb": None,
            "ca": datetime.now().isoformat(),
        })
        db.commit()
        return {"success": True, "link_id": id}
    finally:
        db.close()

@router.delete("/{id}/link/{entity_type}/{entity_id}")
async def unlink_attachment(id: str, entity_type: str, entity_id: str):
    """取消关联"""
    db = get_db_session()
    try:
        if not db.execute(text("SELECT 1 FROM attachments WHERE id = :id"), {"id": id}).fetchone():
            raise HTTPException(404, "附件不存在")

        result = db.execute(text(
            "DELETE FROM attachment_links WHERE attachment_id = :aid AND entity_type = :et AND entity_id = :eid"
        ), {"aid": id, "et": entity_type, "eid": entity_id})
        db.commit()

        if result.rowcount == 0:
            return {"success": False, "message": "未找到关联"}
        return {"success": True}
    finally:
        db.close()

@router.get("")
async def list_attachments(entity_type: str = Query(...), entity_id: str = Query(...)):
    """查询实体的附件列表"""
    db = get_db_session()
    try:
        if entity_type not in VALID_ENTITY_TYPES:
            raise HTTPException(400, {"code": "INVALID_ENTITY", "message": f"不支持的实体类型: {entity_type}"})

        rows = db.execute(text("""
            SELECT a.id, a.filename, a.mime_type, a.file_size, a.sha256_hash, a.created_at, a.created_by
            FROM attachments a
            JOIN attachment_links l ON a.id = l.attachment_id
            WHERE l.entity_type = :et AND l.entity_id = :eid
            ORDER BY a.created_at DESC
        """), {"et": entity_type, "eid": entity_id}).fetchall()

        return {
            "attachments": [{
                "id": r[0], "filename": r[1], "mime_type": r[2],
                "file_size": r[3], "sha256_hash": r[4],
                "created_at": r[5], "created_by": r[6],
            } for r in rows],
            "total": len(rows),
        }
    finally:
        db.close()

@router.head("/{id}")
async def get_attachment_metadata(id: str):
    """获取附件元信息"""
    db = get_db_session()
    try:
        att = db.execute(text(
            "SELECT filename, file_path, mime_type, file_size, sha256_hash, created_at, created_by FROM attachments WHERE id = :id"
        ), {"id": id}).fetchone()

        if not att:
            raise HTTPException(404, "附件不存在")

        return Response(headers={
            "X-Attachment-Filename": att[0],
            "X-Attachment-Size": str(att[3]),
            "X-Attachment-MIME": att[2] or "",
            "X-Attachment-Hash": att[4],
            "X-Attachment-CreatedAt": att[5] or "",
            "X-Attachment-CreatedBy": att[6] or "",
        })
    finally:
        db.close()
