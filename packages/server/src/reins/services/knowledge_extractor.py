# -*- coding: utf-8 -*-
"""
知识自动提取服务 — Sprint 6 task-s6-3

职责：
1. 任务完成后自动提取知识（无论成功/失败）
2. 调用 KF-1 prompt 模板提取关键信息
3. 关联到 industry_pack + capability_tags
4. 写入 knowledge_base 表

铁律：
- 必须用 ORM，禁止 raw SQL
- 禁止 print()，用 logger
- 单文件 ≤ 300 行
"""

import json
import uuid
from loguru import logger
from typing import Dict, Any

from sqlalchemy.orm import Session

from models.task import Task
from models.knowledge import KnowledgeEntry
from models.industry_tag import IndustryPack
from reins.common.database import get_db_session


async def extract_knowledge_from_task(task_id: str) -> Dict[str, Any]:
    """任务完成后自动提取知识，调用 KF-1 并写入 knowledge_base。"""
    session = get_db_session()
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"[KnowledgeExtractor] Task not found: {task_id}")
            return {"success": False, "message": f"Task not found: {task_id}", "knowledge_id": None}
        
        logger.info(f"[KnowledgeExtractor] Extracting knowledge from task: {task_id}")
        is_success = task.status == "done"
        context = {
            "task_id": task.id,
            "task_title": task.title or "",
            "task_description": task.description or "",
            "status": task.status,
            "is_success": is_success,
        }
        
        # 调用 KF-1 Agent 提取知识
        kf_result, kf_error = None, None
        try:
            from services.ai_agent_service import call_agent as _call_agent
            kf_result = _call_agent("KF-1", context)
            logger.info(f"[KnowledgeExtractor] KF-1 result for task {task_id}: {kf_result}")
        except Exception as e:
            kf_error = e
            logger.warning(f"[KnowledgeExtractor] KF-1 call failed for task {task_id}: {e}")
        
        # 解析 KF-1 结果或 fallback
        extracted = _parse_extraction_result(kf_result, kf_error, is_success, task)
        
        # 关联到 industry_pack
        pack_id = _find_or_create_pack_for_task(task, session)
        tags_list = _parse_capability_tags(task.capability_tags)
        
        # 创建 KnowledgeEntry
        knowledge = KnowledgeEntry(
            id=f"kw-{uuid.uuid4().hex[:16]}",
            pack_id=pack_id,
            name=extracted.get("title", f"知识条目_{task.id}"),
            category=extracted.get("knowledge_type", "best_practice"),
            content=extracted.get("content", ""),
            file_path=None,
            version="1.0.0",
            tags=json.dumps(tags_list, ensure_ascii=False) if tags_list else "[]",
            created_at=int(task.created_at or 0),
        )
        
        session.add(knowledge)
        session.commit()
        logger.info(f"[KnowledgeExtractor] Knowledge extracted: {knowledge.id}")
        return {"success": True, "message": f"知识提取成功: {knowledge.id}", "knowledge_id": knowledge.id}
        
    except Exception as e:
        session.rollback()
        logger.error(f"[KnowledgeExtractor] Failed to extract knowledge for task {task_id}: {e}")
        return {"success": False, "message": str(e), "knowledge_id": None}
    finally:
        session.close()


def _parse_extraction_result(kf_result, kf_error, is_success, task):
    """解析 KF-1 结果或生成 fallback 内容。"""
    if kf_error:
        if is_success:
            return {
                "knowledge_type": "best_practice",
                "title": f"最佳实践：{task.title}",
                "content": f"任务成功完成。\n标题：{task.title}\n描述：{task.description}\n结果摘要：{task.result_summary}",
            }
        else:
            return {
                "knowledge_type": "error_pattern",
                "title": f"错误模式：{task.title}",
                "content": f"任务失败。\n标题：{task.title}\n描述：{task.description}\n错误类型：{task.error_type}\n错误信息：{task.error_message}",
            }
    elif kf_result:
        if isinstance(kf_result, dict):
            return {
                "knowledge_type": kf_result.get("knowledge_type", "best_practice" if is_success else "error_pattern"),
                "title": kf_result.get("title", task.title),
                "content": kf_result.get("content", ""),
                "tags": kf_result.get("tags", []),
            }
        else:
            return {
                "knowledge_type": "best_practice" if is_success else "error_pattern",
                "title": f"知识条目：{task.title}",
                "content": str(kf_result),
            }
    else:
        return {
            "knowledge_type": "best_practice" if is_success else "error_pattern",
            "title": f"知识条目：{task.title}",
            "content": f"任务{'成功' if is_success else '失败'}完成，但未提取到详细信息",
        }


def _find_or_create_pack_for_task(task: Task, session: Session) -> str:
    """为任务查找或创建 industry_pack。"""
    # 1. 尝试从 goal/project 获取 pack_id
    if task.goal_id:
        pack = session.query(IndustryPack).filter(IndustryPack.id == task.goal_id).first()
        if pack:
            return pack.id
    if task.project_id:
        pack = session.query(IndustryPack).filter(IndustryPack.id == task.project_id).first()
        if pack:
            return pack.id
    
    # 2. 使用默认 pack
    default_pack = session.query(IndustryPack).filter(IndustryPack.name == "通用知识").first()
    if default_pack:
        return default_pack.id
    
    # 3. 创建默认 pack
    import datetime
    now = int(datetime.datetime.now().timestamp())
    default_pack = IndustryPack(
        id=f"pack-general-{uuid.uuid4().hex[:8]}",
        name="通用知识",
        description="通用知识包，用于没有明确行业归属的知识条目",
        created_at=now,
    )
    session.add(default_pack)
    session.commit()
    return default_pack.id


def _parse_capability_tags(capability_tags) -> list:
    """解析 capability_tags JSON 字段，提取 tag ID 列表。"""
    tags_list = []
    try:
        cap_tags = json.loads(capability_tags) if isinstance(capability_tags, str) else capability_tags
        if isinstance(cap_tags, dict):
            for category, tag_ids in cap_tags.items():
                if isinstance(tag_ids, list):
                    tags_list.extend(tag_ids)
                elif tag_ids:
                    tags_list.append(str(tag_ids))
    except Exception:
        pass
    return tags_list


def inject_knowledge(task: Task, session: Session) -> list:
    """根据 task 的 capability_tags 从 knowledge_base 查询相关条目。"""
    try:
        tag_ids = _parse_capability_tags(task.capability_tags)
        if not tag_ids:
            return []
        
        knowledge_entries = session.query(KnowledgeEntry).all()
        results = []
        
        for entry in knowledge_entries:
            entry_tags = []
            try:
                if entry.tags:
                    entry_tags = json.loads(entry.tags) if isinstance(entry.tags, str) else entry.tags
                    if not isinstance(entry_tags, list):
                        entry_tags = [entry_tags] if entry_tags else []
            except (json.JSONDecodeError, TypeError):
                entry_tags = []
            
            matching_tags = set(tag_ids) & set(entry_tags)
            relevance = len(matching_tags)
            if relevance > 0:
                results.append({
                    "knowledge_id": entry.id,
                    "title": entry.name or "",
                    "content": entry.content or "",
                    "category": entry.category or "general",
                    "relevance": relevance,
                })
        
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:5]
    except Exception as e:
        logger.warning(f"[inject_knowledge] Failed to inject knowledge: {e}")
        return []
