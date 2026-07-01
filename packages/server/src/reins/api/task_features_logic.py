"""任务特性逻辑模块"""

import uuid
import json
import os
import mimetypes
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from models import Task, TaskComment, ExecutionLog, TaskRelation, Attachment, AttachmentLink


def _parse_metadata(meta_field) -> Dict[str, Any]:
    """解析 metadata 字段"""
    if meta_field:
        try:
            return json.loads(meta_field)
        except Exception:
            pass
    return {}


def _serialize_metadata(meta: Any) -> Optional[str]:
    """序列化 metadata 为 JSON 字符串"""
    if meta and isinstance(meta, dict):
        return json.dumps(meta, ensure_ascii=False)
    return None


def _get_task_comments(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务评论"""
    rows = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(
        TaskComment.created_at.asc()
    ).all()
    comments = []
    for row in rows:
        meta = _parse_metadata(row.metadata)
        comments.append({
            "id": row.id,
            "task_id": row.task_id,
            "author": row.author,
            "author_role": row.author_role,
            "type": row.type,
            "content": row.content,
            "is_agent_reply": bool(row.is_agent_reply),
            "metadata": meta,
            "created_at": row.created_at,
        })
    return comments


def _add_task_comment(db, task_id: str, author: str, content: str, is_agent_reply: bool, comment_type: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """添加任务评论"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    comment_id = f"{uuid.uuid4().hex[:8]}"
    created_at = datetime.utcnow()
    metadata_json = _serialize_metadata(metadata)
    db.add(TaskComment(
        id=comment_id,
        task_id=task_id,
        author=author,
        content=content,
        is_agent_reply=is_agent_reply,
        created_at=created_at,
        author_role="human" if not is_agent_reply else "agent",
        type=comment_type,
        metadata=metadata_json,
    ))
    if comment_type == "discussion":
        db.query(Task).filter(Task.id == task_id).update({
            "status": "review_needed",
            "updated_at": created_at,
        })
    db.commit()
    return {
        "id": comment_id,
        "task_id": task_id,
        "author": author,
        "content": content,
        "is_agent_reply": bool(is_agent_reply),
        "type": comment_type,
        "created_at": created_at,
    }


def _delete_task_comment(db, task_id: str, comment_id: str) -> None:
    """删除任务评论"""
    comment = db.query(TaskComment).filter(
        TaskComment.id == comment_id,
        TaskComment.task_id == task_id,
    ).first()
    if not comment:
        raise ValueError("评论不存在或不属于此任务")
    db.delete(comment)
    db.commit()


def _get_execution_logs(db, task_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """获取任务执行日志"""
    rows = db.query(ExecutionLog).filter(
        ExecutionLog.task_id == task_id
    ).order_by(
        ExecutionLog.created_at.desc()
    ).limit(limit).offset(offset).all()
    total = db.query(ExecutionLog).filter(ExecutionLog.task_id == task_id).count()
    logs = []
    for row in rows:
        row_dict = {
            "id": row.id,
            "task_id": row.task_id,
            "agent_id": row.agent_id,
            "action": row.action,
            "input": _parse_metadata(row.input) if row.input else {},
            "output": _parse_metadata(row.output) if row.output else {},
            "status": row.status,
            "duration_ms": row.duration_ms,
            "created_at": row.created_at,
            "error_message": row.error_message,
            "result_summary": row.result_summary,
            "metadata": _parse_metadata(row.metadata) if row.metadata else {},
        }
        logs.append(row_dict)
    return {"success": True, "task_id": task_id, "logs": logs, "total": total, "limit": limit, "offset": offset}


def _get_task_sub_issues(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务子任务和关联"""
    relations = db.query(TaskRelation).filter(
        TaskRelation.parent_task_id == task_id
    ).all()
    result = []
    for rel in relations:
        child_task = db.query(Task).with_entities(
            Task.id, Task.title, Task.description, Task.status
        ).filter(Task.id == rel.child_task_id).first()
        result.append({
            "id": rel.id,
            "parent_task_id": rel.parent_task_id,
            "child_task_id": rel.child_task_id,
            "relation_type": rel.relation_type,
            "created_at": rel.created_at,
            "child_task_info": {
                "id": child_task[0],
                "title": child_task[1],
                "description": child_task[2],
                "status": child_task[3],
            } if child_task else None,
        })
    return result


def _add_task_sub_issue(db, task_id: str, child_task_id: str, relation_type: str) -> Dict[str, Any]:
    """添加任务关联"""
    if task_id == child_task_id:
        raise ValueError("任务不能关联到自身")
    parent = db.query(Task).filter(Task.id == task_id).first()
    if not parent:
        raise ValueError("父任务不存在")
    child = db.query(Task).filter(Task.id == child_task_id).first()
    if not child:
        raise ValueError("子任务不存在")
    relation_id = f"{uuid.uuid4().hex[:8]}"
    created_at = datetime.utcnow()
    db.add(TaskRelation(
        id=relation_id,
        parent_task_id=task_id,
        child_task_id=child_task_id,
        relation_type=relation_type,
        created_at=created_at,
    ))
    db.commit()
    return {
        "id": relation_id,
        "parent_task_id": task_id,
        "child_task_id": child_task_id,
        "relation_type": relation_type,
        "created_at": created_at,
    }


def _delete_task_sub_issue(db, task_id: str, relation_id: str) -> None:
    """删除任务关联"""
    rel = db.query(TaskRelation).filter(
        TaskRelation.id == relation_id,
        TaskRelation.parent_task_id == task_id,
    ).first()
    if not rel:
        raise ValueError("关联不存在或不属于此任务")
    db.delete(rel)
    db.commit()


def _get_task_attachments(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务附件（统一附件系统）"""
    rows = db.query(Attachment).join(
        AttachmentLink, Attachment.id == AttachmentLink.attachment_id
    ).filter(
        AttachmentLink.entity_type == 'task',
        AttachmentLink.entity_id == task_id,
    ).order_by(Attachment.created_at.asc()).all()
    return [
        {
            "id": row.id,
            "task_id": task_id,
            "filename": row.filename,
            "mime_type": row.mime_type,
            "file_size": row.file_size,
            "uploaded_by": row.created_by,
            "created_at": row.created_at,
        }
        for row in rows
    ]


import asyncio

async def _upload_task_attachment(db, task_id: str, file, uploaded_by: str = "system") -> Dict[str, Any]:
    """上传任务附件（统一附件系统）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    attachments_dir = str(Path(__file__).resolve().parents[5] / "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    file_path = os.path.join(attachments_dir, unique_filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    attachment_id = f"{uuid.uuid4().hex[:8]}"
    created_at = datetime.utcnow()
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    file_size = len(content)
    sha256_hash = hashlib.sha256(content).hexdigest()
    # 写入 attachments 表
    db.add(Attachment(
        id=attachment_id,
        filename=unique_filename,
        file_path=file_path,
        mime_type=mime_type,
        sha256_hash=sha256_hash,
        file_size=file_size,
        created_by=uploaded_by,
        created_at=created_at,
    ))
    # 写入 attachment_links 表
    link_id = f"link-{uuid.uuid4().hex[:8]}"
    db.add(AttachmentLink(
        id=link_id,
        attachment_id=attachment_id,
        entity_type='task',
        entity_id=task_id,
        created_by=uploaded_by,
        created_at=created_at,
    ))
    db.commit()
    return {
        "id": attachment_id,
        "task_id": task_id,
        "filename": unique_filename,
        "mime_type": mime_type,
        "file_size": file_size,
    }


def _delete_task_attachment(db, task_id: str, attachment_id: str, logger) -> None:
    """删除任务附件（统一附件系统）"""
    from sqlalchemy import func
    att_row = db.query(Attachment).join(
        AttachmentLink, Attachment.id == AttachmentLink.attachment_id
    ).filter(
        AttachmentLink.attachment_id == attachment_id,
        AttachmentLink.entity_type == 'task',
        AttachmentLink.entity_id == task_id,
    ).first()
    if not att_row:
        raise ValueError("附件不存在或不属于此任务")
    file_path = att_row.file_path
    # 删除链接
    db.query(AttachmentLink).filter(
        AttachmentLink.attachment_id == attachment_id,
        AttachmentLink.entity_type == 'task',
        AttachmentLink.entity_id == task_id,
    ).delete()
    # 检查是否还有其他链接
    link_count = db.query(func.count(AttachmentLink.id)).filter(
        AttachmentLink.attachment_id == attachment_id
    ).scalar()
    if link_count == 0:
        db.query(Attachment).filter(Attachment.id == attachment_id).delete()
    db.commit()
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.info(f"警告: 删除附件文件失败 {file_path}: {str(e)}")


async def _upload_task_attachment_async(db, task_id: str, file, uploaded_by: str = "system"):
    """异步上传任务附件"""
    return await _upload_task_attachment(db, task_id, file, uploaded_by)