"""任务特性逻辑模块"""

import uuid
import json
import os
import mimetypes
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import text

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

def _get_task_labels(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务标签"""
    query = text("SELECT id, task_id, name, color, created_at FROM task_labels WHERE task_id = :task_id ORDER BY created_at ASC")
    result = db.execute(query, {"task_id": task_id})
    rows = result.fetchall()
    labels = []
    for row in rows:
        labels.append({"id": row[0], "task_id": row[1], "name": row[2], "color": row[3], "created_at": row[4]})
    return labels

def _add_task_label(db, task_id: str, name: str, color: str) -> Dict[str, Any]:
    """添加任务标签"""
    task_query = text("SELECT id FROM tasks WHERE id = :task_id")
    task_result = db.execute(task_query, {"task_id": task_id})
    if not task_result.fetchone():
        raise ValueError("任务不存在")
    label_id = f"{uuid.uuid4().hex[:8]}"
    created_at = datetime.now()
    insert_query = text("""
        INSERT INTO task_labels (id, task_id, name, color, created_at)
        VALUES (:id, :task_id, :name, :color, :created_at)
    """)
    db.execute(insert_query, {"id": label_id, "task_id": task_id, "name": name, "color": color, "created_at": created_at})
    db.commit()
    return {"id": label_id, "task_id": task_id, "name": name, "color": color, "created_at": created_at}

def _delete_task_label(db, task_id: str, label_id: str) -> None:
    """删除任务标签"""
    query = text("SELECT id FROM task_labels WHERE id = :label_id AND task_id = :task_id")
    result = db.execute(query, {"label_id": label_id, "task_id": task_id})
    if not result.fetchone():
        raise ValueError("标签不存在或不属于此任务")
    delete_query = text("DELETE FROM task_labels WHERE id = :label_id AND task_id = :task_id")
    db.execute(delete_query, {"label_id": label_id, "task_id": task_id})
    db.commit()

def _get_all_labels(db) -> List[Dict[str, Any]]:
    """获取所有标签（去重，按使用次数排序）"""
    query = text("SELECT name, color, COUNT(*) as usage_count FROM task_labels GROUP BY name, color ORDER BY usage_count DESC")
    result = db.execute(query)
    rows = result.fetchall()
    labels = []
    for row in rows:
        labels.append({"name": row[0], "color": row[1], "usage_count": row[2]})
    return labels

def _get_task_comments(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务评论"""
    query = text("SELECT id, task_id, author, author_role, type, content, is_agent_reply, metadata, created_at FROM task_comments WHERE task_id = :task_id ORDER BY created_at ASC")
    result = db.execute(query, {"task_id": task_id})
    rows = result.fetchall()
    comments = []
    for row in rows:
        meta = _parse_metadata(row[7])
        comments.append({"id": row[0], "task_id": row[1], "author": row[2], "author_role": row[3], "type": row[4], "content": row[5], "is_agent_reply": bool(row[6]), "metadata": meta, "created_at": row[8]})
    return comments

def _add_task_comment(db, task_id: str, author: str, content: str, is_agent_reply: bool, comment_type: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """添加任务评论"""
    task_query = text("SELECT id, status, assigned_agent FROM tasks WHERE id = :task_id")
    task_result = db.execute(task_query, {"task_id": task_id})
    task_row = task_result.fetchone()
    if not task_row:
        raise ValueError("任务不存在")
    comment_id = f"{uuid.uuid4().hex[:8]}"
    created_at = datetime.now()
    metadata_json = _serialize_metadata(metadata)
    insert_query = text("""
        INSERT INTO task_comments (id, task_id, author, content, is_agent_reply, created_at, author_role, type, metadata)
        VALUES (:id, :task_id, :author, :content, :is_agent_reply, :created_at, :author_role, :type, :metadata)
    """)
    db.execute(insert_query, {"id": comment_id, "task_id": task_id, "author": author, "content": content, "is_agent_reply": int(is_agent_reply), "created_at": created_at, "author_role": "human" if not is_agent_reply else "agent", "type": comment_type, "metadata": metadata_json})
    if comment_type == "discussion":
        db.execute(text("UPDATE tasks SET status = 'review_needed', updated_at = :now WHERE id = :task_id"), {"task_id": task_id, "now": created_at})
    db.commit()
    return {"id": comment_id, "task_id": task_id, "author": author, "content": content, "is_agent_reply": bool(is_agent_reply), "type": comment_type, "created_at": created_at}

def _delete_task_comment(db, task_id: str, comment_id: str) -> None:
    """删除任务评论"""
    query = text("SELECT id FROM task_comments WHERE id = :comment_id AND task_id = :task_id")
    result = db.execute(query, {"comment_id": comment_id, "task_id": task_id})
    if not result.fetchone():
        raise ValueError("评论不存在或不属于此任务")
    delete_query = text("DELETE FROM task_comments WHERE id = :comment_id AND task_id = :task_id")
    db.execute(delete_query, {"comment_id": comment_id, "task_id": task_id})
    db.commit()

def _get_execution_logs(db, task_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """获取任务执行日志"""
    query = text("""
        SELECT id, task_id, agent_id, action, input, output, status, duration_ms, created_at, error_message, result_summary, metadata
        FROM execution_logs
        WHERE task_id = :task_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, {"task_id": task_id, "limit": limit, "offset": offset}).fetchall()
    count_query = text("SELECT COUNT(*) FROM execution_logs WHERE task_id = :task_id")
    total = db.execute(count_query, {"task_id": task_id}).scalar()
    logs = []
    for row in rows:
        row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(zip(
            ["id", "task_id", "agent_id", "action", "input", "output", "status", "duration_ms", "created_at", "error_message", "result_summary", "metadata"],
            row
        ))
        for field in ["input", "output", "metadata"]:
            if row_dict.get(field):
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except Exception:
                    row_dict[field] = {}
            else:
                row_dict[field] = {}
        logs.append(row_dict)
    return {"success": True, "task_id": task_id, "logs": logs, "total": total, "limit": limit, "offset": offset}

def _get_task_sub_issues(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务子任务和关联"""
    query = text("""
        SELECT tr.id, tr.parent_task_id, tr.child_task_id, tr.relation_type, tr.created_at,
               t.title as child_title, t.description as child_description, t.status as child_status
        FROM task_relations tr
        LEFT JOIN tasks t ON tr.child_task_id = t.id
        WHERE tr.parent_task_id = :task_id
        ORDER BY tr.created_at ASC
    """)
    result = db.execute(query, {"task_id": task_id})
    rows = result.fetchall()
    relations = []
    for row in rows:
        relations.append({
            "id": row[0], "parent_task_id": row[1], "child_task_id": row[2], "relation_type": row[3], "created_at": row[4],
            "child_task_info": {"id": row[2], "title": row[5], "description": row[6], "status": row[7]} if row[2] else None
        })
    return relations

def _add_task_sub_issue(db, task_id: str, child_task_id: str, relation_type: str) -> Dict[str, Any]:
    """添加任务关联"""
    if task_id == child_task_id:
        raise ValueError("任务不能关联到自身")
    parent_query = text("SELECT id FROM tasks WHERE id = :task_id")
    parent_result = db.execute(parent_query, {"task_id": task_id})
    if not parent_result.fetchone():
        raise ValueError("父任务不存在")
    child_query = text("SELECT id FROM tasks WHERE id = :child_task_id")
    child_result = db.execute(child_query, {"child_task_id": child_task_id})
    if not child_result.fetchone():
        raise ValueError("子任务不存在")
    relation_id = f"{uuid.uuid4().hex[:8]}"
    created_at = datetime.now()
    insert_query = text("""
        INSERT INTO task_relations (id, parent_task_id, child_task_id, relation_type, created_at)
        VALUES (:id, :parent_task_id, :child_task_id, :relation_type, :created_at)
    """)
    db.execute(insert_query, {"id": relation_id, "parent_task_id": task_id, "child_task_id": child_task_id, "relation_type": relation_type, "created_at": created_at})
    db.commit()
    return {"id": relation_id, "parent_task_id": task_id, "child_task_id": child_task_id, "relation_type": relation_type, "created_at": created_at}

def _delete_task_sub_issue(db, task_id: str, relation_id: str) -> None:
    """删除任务关联"""
    query = text("SELECT id FROM task_relations WHERE id = :relation_id AND parent_task_id = :task_id")
    result = db.execute(query, {"relation_id": relation_id, "task_id": task_id})
    if not result.fetchone():
        raise ValueError("关联不存在或不属于此任务")
    delete_query = text("DELETE FROM task_relations WHERE id = :relation_id AND parent_task_id = :task_id")
    db.execute(delete_query, {"relation_id": relation_id, "task_id": task_id})
    db.commit()

def _get_task_attachments(db, task_id: str) -> List[Dict[str, Any]]:
    """获取任务附件（统一附件系统）"""
    query = text("""
        SELECT a.id, a.filename, a.mime_type, a.file_size, a.created_by, a.created_at
        FROM attachments a
        JOIN attachment_links al ON a.id = al.attachment_id
        WHERE al.entity_type = 'task' AND al.entity_id = :task_id
        ORDER BY a.created_at ASC
    """)
    result = db.execute(query, {"task_id": task_id})
    rows = result.fetchall()
    return [
        {
            "id": row[0], "task_id": task_id, "filename": row[1],
            "mime_type": row[2], "file_size": row[3],
            "uploaded_by": row[4], "created_at": row[5]
        }
        for row in rows
    ]

import asyncio

async def _upload_task_attachment(db, task_id: str, file, uploaded_by: str = "system") -> Dict[str, Any]:
    """上传任务附件（统一附件系统）"""
    task_query = text("SELECT id FROM tasks WHERE id = :task_id")
    task_result = db.execute(task_query, {"task_id": task_id})
    if not task_result.fetchone():
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
    created_at = datetime.now()
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    file_size = len(content)
    sha256_hash = ""
    # 写入 attachments 表
    db.execute(text("""
        INSERT INTO attachments (id, filename, file_path, mime_type, sha256_hash, file_size, created_by, created_at)
        VALUES (:id, :filename, :file_path, :mime_type, :sha256_hash, :file_size, :created_by, :created_at)
    """), {"id": attachment_id, "filename": unique_filename, "file_path": file_path,
           "mime_type": mime_type, "sha256_hash": sha256_hash, "file_size": file_size,
           "created_by": uploaded_by, "created_at": created_at})
    # 写入 attachment_links 表
    link_id = f"link-{uuid.uuid4().hex[:8]}"
    db.execute(text("""
        INSERT INTO attachment_links (id, attachment_id, entity_type, entity_id, created_by, created_at)
        VALUES (:id, :attachment_id, 'task', :entity_id, :created_by, :created_at)
    """), {"id": link_id, "attachment_id": attachment_id, "entity_id": task_id,
           "created_by": uploaded_by, "created_at": created_at})
    db.commit()
    return {"id": attachment_id, "task_id": task_id, "filename": unique_filename,
            "mime_type": mime_type, "file_size": file_size}

def _delete_task_attachment(db, task_id: str, attachment_id: str, logger) -> None:
    """删除任务附件（统一附件系统）"""
    query = text("""
        SELECT a.file_path FROM attachments a
        JOIN attachment_links al ON a.id = al.attachment_id
        WHERE al.attachment_id = :attachment_id AND al.entity_type = 'task' AND al.entity_id = :task_id
    """)
    result = db.execute(query, {"attachment_id": attachment_id, "task_id": task_id})
    row = result.fetchone()
    if not row:
        raise ValueError("附件不存在或不属于此任务")
    file_path = row[0]
    # 删除链接
    db.execute(text("DELETE FROM attachment_links WHERE attachment_id = :attachment_id AND entity_type = 'task' AND entity_id = :task_id"),
               {"attachment_id": attachment_id, "task_id": task_id})
    # 检查是否还有其他链接
    link_count = db.execute(text("SELECT COUNT(*) FROM attachment_links WHERE attachment_id = :attachment_id"),
                            {"attachment_id": attachment_id}).fetchone()[0]
    if link_count == 0:
        db.execute(text("DELETE FROM attachments WHERE id = :attachment_id"), {"attachment_id": attachment_id})
    db.commit()
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.info(f"警告: 删除附件文件失败 {file_path}: {str(e)}")

async def _upload_task_attachment_async(db, task_id: str, file, uploaded_by: str = "system"):
    """异步上传任务附件"""
    return await _upload_task_attachment(db, task_id, file, uploaded_by)