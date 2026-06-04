"""任务特性 API (Facade)"""

from loguru import logger
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from sqlalchemy import text
import uuid
import os
from datetime import datetime
from typing import List, Optional

from reins.common.database import get_db
from .task_features_logic import _get_task_labels, _add_task_label, _delete_task_label, _get_all_labels, _get_task_comments, _add_task_comment, _delete_task_comment, _get_execution_logs, _get_task_sub_issues, _add_task_sub_issue, _delete_task_sub_issue, _get_task_attachments, _upload_task_attachment_async, _delete_task_attachment

router = APIRouter(prefix="/api/v1/tasks", tags=["task-features"])

@router.get("/{task_id}/labels")
async def get_task_labels(task_id: str):
    """返回指定任务的所有标签"""
    db = next(get_db())
    try:
        return _get_task_labels(db, task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签失败: {str(e)}")
    finally:
        db.close()

@router.post("/{task_id}/labels")
async def add_task_label(task_id: str, label_data: dict):
    """为任务添加标签"""
    name = label_data.get("name")
    color = label_data.get("color")
    if not name or not color:
        raise HTTPException(status_code=400, detail="标签名称和颜色不能为空")
    db = next(get_db())
    try:
        return _add_task_label(db, task_id, name, color)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加标签失败: {str(e)}")
    finally:
        db.close()

@router.delete("/{task_id}/labels/{label_id}")
async def delete_task_label(task_id: str, label_id: str):
    """删除任务的指定标签"""
    db = next(get_db())
    try:
        _delete_task_label(db, task_id, label_id)
        return {"message": "标签删除成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除标签失败: {str(e)}")
    finally:
        db.close()

@router.get("/labels/all")
async def get_all_labels():
    """返回所有可用标签"""
    db = next(get_db())
    try:
        return _get_all_labels(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取所有标签失败: {str(e)}")
    finally:
        db.close()

@router.get("/{task_id}/comments")
async def get_task_comments(task_id: str):
    """返回指定任务的所有评论"""
    db = next(get_db())
    try:
        return _get_task_comments(db, task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取评论失败: {str(e)}")
    finally:
        db.close()

@router.post("/{task_id}/comments")
async def add_task_comment(task_id: str, comment_data: dict):
    """为任务添加评论"""
    author = comment_data.get("author")
    content = comment_data.get("content")
    is_agent_reply = comment_data.get("is_agent_reply", False)
    comment_type = comment_data.get("type", "comment")
    if not author or not content:
        raise HTTPException(status_code=400, detail="评论作者和内容不能为空")
    db = next(get_db())
    try:
        return _add_task_comment(db, task_id, author, content, is_agent_reply, comment_type, comment_data.get("metadata"))
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加评论失败: {str(e)}")
    finally:
        db.close()

@router.delete("/{task_id}/comments/{comment_id}")
async def delete_task_comment(task_id: str, comment_id: str):
    """删除任务的指定评论"""
    db = next(get_db())
    try:
        _delete_task_comment(db, task_id, comment_id)
        return {"message": "评论删除成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除评论失败: {str(e)}")
    finally:
        db.close()

@router.get("/{task_id}/execution-logs")
async def get_task_execution_logs(task_id: str, limit: int = 50, offset: int = 0):
    """按 task_id 查询 execution_logs"""
    db = next(get_db())
    try:
        return _get_execution_logs(db, task_id, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询执行日志失败: {str(e)}")
    finally:
        db.close()

@router.get("/{task_id}/sub-issues")
async def get_task_sub_issues(task_id: str):
    """返回指定任务的子任务和关联列表"""
    db = next(get_db())
    try:
        return _get_task_sub_issues(db, task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取子任务和关联失败: {str(e)}")
    finally:
        db.close()

@router.post("/{task_id}/sub-issues")
async def add_task_sub_issue(task_id: str, relation_data: dict):
    """为任务添加关联"""
    child_task_id = relation_data.get("child_task_id")
    relation_type = relation_data.get("relation_type")
    valid_relation_types = ["subtask", "blocks", "relates_to"]
    if not child_task_id or relation_type not in valid_relation_types:
        raise HTTPException(status_code=400, detail="子任务ID和关系类型不能为空")
    if task_id == child_task_id:
        raise HTTPException(status_code=400, detail="任务不能关联到自身")
    db = next(get_db())
    try:
        return _add_task_sub_issue(db, task_id, child_task_id, relation_type)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加关联失败: {str(e)}")
    finally:
        db.close()

@router.delete("/{task_id}/sub-issues/{relation_id}")
async def delete_task_sub_issue(task_id: str, relation_id: str):
    """删除任务的指定关联"""
    db = next(get_db())
    try:
        _delete_task_sub_issue(db, task_id, relation_id)
        return {"message": "关联删除成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除关联失败: {str(e)}")
    finally:
        db.close()

@router.get("/{task_id}/attachments")
async def get_task_attachments(task_id: str):
    """返回指定任务的所有附件"""
    db = next(get_db())
    try:
        return _get_task_attachments(db, task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取附件失败: {str(e)}")
    finally:
        db.close()

@router.post("/{task_id}/attachments")
async def upload_task_attachment(task_id: str, file: UploadFile = File(...)):
    """上传任务附件"""
    db = next(get_db())
    try:
        return await _upload_task_attachment_async(db, task_id, file)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传附件失败: {str(e)}")
    finally:
        db.close()

@router.get("/{task_id}/attachments/{attachment_id}/download")
async def download_task_attachment(task_id: str, attachment_id: str):
    """下载任务附件"""
    db = next(get_db())
    try:
        query = text("""
            SELECT a.file_path, a.filename FROM attachments a
            JOIN attachment_links al ON a.id = al.attachment_id
            WHERE al.attachment_id = :attachment_id AND al.entity_type = 'task' AND al.entity_id = :task_id
        """)
        result = db.execute(query, {"attachment_id": attachment_id, "task_id": task_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="附件不存在或不属于此任务")
        file_path = row[0]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="附件文件不存在")
        return FileResponse(path=file_path, filename=row[1], media_type='application/octet-stream')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载附件失败: {str(e)}")
    finally:
        db.close()

@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_task_attachment(task_id: str, attachment_id: str):
    """删除任务附件"""
    db = next(get_db())
    try:
        _delete_task_attachment(db, task_id, attachment_id, logger)
        return {"message": "附件删除成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除附件失败: {str(e)}")
    finally:
        db.close()