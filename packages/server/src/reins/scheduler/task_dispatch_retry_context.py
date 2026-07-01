"""重派任务的 DP-1 context 构建器"""
from typing import Dict, Any
from models.task import Task
from models.industry_tag import IndustryCapabilityTag
from models.knowledge import KnowledgeEntry
from models.project import Project
from models.goal import Goal
from reins.common.database import get_db_session
import json
from loguru import logger


def build_dispatch_retry_context(task: Task) -> Dict[str, Any]:
    """
    构建重派任务的上下文（用于 DP-1 prompt 模板）
    
    Args:
        task: Task ORM 实例
        
    Returns:
        字典，包含：
        - task_title: 任务标题
        - task_description: 任务描述
        - project_name: 项目名称
        - goal_title: 目标标题
        - failure_reason: 之前的失败原因
        - retry_count: 重派次数
        - dispatch_report: 调度报告（简要）
        - lessons_learned: 从前次失败中提取的教训
        - acceptance_criteria: 验收标准
        - process_standards: 过程标准
        - depends_on_info: 依赖信息
        - project_context: 项目上下文
        - knowledge_injection: 知识注入
    """
    context = {}
    
    # 1. 任务基本信息
    context["task_title"] = task.title or ""
    context["task_description"] = task.description or ""
    
    # 2. 项目信息
    if task.project_id:
        try:
            session = get_db_session()
            try:
                project = session.query(Project).filter(Project.id == task.project_id).first()
                if project:
                    context["project_name"] = project.name or ""
                else:
                    context["project_name"] = "未知项目"
            finally:
                session.close()
        except Exception:
            context["project_name"] = "未知项目"
    else:
        context["project_name"] = "未知项目"
    
    # 3. 目标信息
    if task.goal_id:
        try:
            session = get_db_session()
            try:
                goal = session.query(Goal).filter(Goal.id == task.goal_id).first()
                if goal:
                    context["goal_title"] = goal.title or ""
                else:
                    context["goal_title"] = "未知目标"
            finally:
                session.close()
        except Exception:
            context["goal_title"] = "未知目标"
    else:
        context["goal_title"] = "未知目标"
    
    # 4. 失败原因（从 loop_context 读取）
    loop_context = {}
    if task.loop_context:
        try:
            loop_context = json.loads(task.loop_context) if isinstance(
                task.loop_context, str) else task.loop_context
        except Exception:
            pass
    context["failure_reason"] = loop_context.get("reason", "未知原因") or "未知原因"
    
    # 5. 重派次数
    context["retry_count"] = task.dispatch_attempt or 1
    
    # 6. 调度报告（简要）
    retry_history = loop_context.get("retry_history", [])
    dispatch_report_parts = []
    for entry in retry_history[-3:]:  # 最近 3 次
        dispatch_report_parts.append(f"Attempt {entry.get('attempt', '?')}: {entry.get('reason', 'unknown')}")
    context["dispatch_report"] = "\n".join(dispatch_report_parts) if dispatch_report_parts else "首次重派"
    
    # 7. 从 loop_context 中提取教训
    lessons = []
    if loop_context.get("reason"):
        lessons.append(f"- 前次失败原因：{loop_context.get('reason')}")
    if loop_context.get("original_agent"):
        lessons.append(f"- 原执行 Agent：{loop_context.get('original_agent')}")
    if retry_history:
        lessons.append(f"- 总重派次数：{len(retry_history)}")
    context["lessons_learned"] = "\n".join(lessons) if lessons else "无历史教训"
    
    # 8. 验收标准
    context["acceptance_criteria"] = task.acceptance_criteria or ""
    
    # 9. 过程标准（从 capability_tags 提取）
    try:
        capability_tags = json.loads(task.capability_tags) if isinstance(
            task.capability_tags, str) else task.capability_tags
        technical_tags = capability_tags.get("technical", [])
        if isinstance(technical_tags, str):
            technical_tags = json.loads(technical_tags)
        elif not isinstance(technical_tags, list):
            technical_tags = [technical_tags] if technical_tags else []
        
        # 从 industry_capability_tags 表获取 standards
        process_standards = []
        session = get_db_session()
        try:
            for tag_id in technical_tags[:5]:
                tag_row = session.query(IndustryCapabilityTag).filter(
                    IndustryCapabilityTag.id == tag_id
                ).first()
                if tag_row and tag_row.standards:
                    try:
                        standards = json.loads(tag_row.standards)
                        if isinstance(standards, list):
                            process_standards.extend(standards)
                    except Exception:
                        pass
        finally:
            session.close()
        
        context["process_standards"] = "\n".join(process_standards[:10]) if process_standards else ""
    except Exception as e:
        logger.warning(f"Failed to merge process_standards for task {task.id}: {e}")
        context["process_standards"] = ""
    
    # 10. 依赖关系
    try:
        depends_on = json.loads(task.depends_on) if isinstance(
            task.depends_on, str) else task.depends_on or []
        context["depends_on_info"] = "、".join(depends_on) if depends_on else "无依赖"
    except Exception:
        context["depends_on_info"] = "无依赖"
    
    # 11. 项目上下文
    context["project_context"] = task.context_md or ""
    
    # 12. 知识注入（简单版本）
    try:
        knowledge_entries = []
        search_terms = [task.title, task.description]
        session = get_db_session()
        try:
            for term in search_terms:
                if term and len(term) > 5:
                    rows = session.query(KnowledgeEntry).filter(
                        KnowledgeEntry.status == "active"
                    ).filter(
                        KnowledgeEntry.title.like(f"%{term}%") |
                        KnowledgeEntry.content.like(f"%{term}%")
                    ).limit(2).all()
                    for row in rows:
                        knowledge_entries.append(f"- {row.title or 'Unknown'}: {row.content[:100] if row.content else ''}")
        finally:
            session.close()
        context["knowledge_injection"] = "\n".join(knowledge_entries) if knowledge_entries else ""
    except Exception:
        context["knowledge_injection"] = ""
    
    return context
