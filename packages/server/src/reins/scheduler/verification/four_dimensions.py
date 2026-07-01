"""
四维度验证引擎

职责：
1. 四维度验证逻辑实现
2. 使用 V-1 prompt 模板调用验证 Agent
3. 验证结果写入 DB

四维度：
1. business_result - 业务结果验证
2. cross_task_consistency - 跨任务一致性
3. goal_alignment - 目标对齐
4. quality - 质量判断
"""

import asyncio
import json
from typing import Dict, Any, Optional

from loguru import logger

from models import Task, Goal, PromptLibrary
from reins.common.database import get_db_manager
from sqlalchemy import select


def _get_v1_prompt_template() -> Optional[str]:
    """获取 V-1 prompt 模板"""
    try:
        db = get_db_manager()
        session = db.get_session()
        query = select(PromptLibrary)\
            .where(PromptLibrary.id == 'V-1')\
            .where(PromptLibrary.status == 'active')\
            .order_by(PromptLibrary.version.desc())\
            .limit(1)
        result = session.execute(query).scalar_one_or_none()
        session.close()
        return result.content if result else None
    except Exception as e:
        logger.error(f"Failed to get V-1 prompt template: {e}")
        return None


def _build_context(task: Task, project_tasks: list, goal: Optional[Goal] = None, verification_round: int = 0) -> Dict[str, Any]:
    """构建四维度验证上下文"""
    # 跨任务信息
    project_tasks_info = [{
        "task_id": t.id,
        "title": t.title,
        "status": t.status,
        "result_summary": t.result_summary,
        "acceptance_criteria": t.acceptance_criteria,
    } for t in project_tasks]
    
    # 目标上下文
    goal_context = None
    if goal:
        goal_context = {
            "goal_id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "context_md": goal.context_md,
        }
    
    # 通用质量标准
    quality_standards = {
        "code_quality": {"py_compile": "必须通过", "pep8": "符合 PEP 8"},
        "documentation": {"readme": "必须有 README"},
        "maintainability": {"modular": "代码模块化", "commented": "关键逻辑有注释"},
    }
    
    return {
        "acceptance_criteria": task.acceptance_criteria or "{}",
        "self_review_report": getattr(task, 'self_review_report', None) or "{}",
        "project_tasks": json.dumps(project_tasks_info, ensure_ascii=False),
        "goal_context": json.dumps(goal_context, ensure_ascii=False) if goal_context else None,
        "quality_standards": json.dumps(quality_standards, ensure_ascii=False),
        "task_id": task.id,
        "task_title": task.title,
        "result_summary": task.result_summary or "",
        "verification_round": verification_round,
    }


async def _call_verifier_agent(context: Dict[str, Any]) -> Dict[str, Any]:
    """调用 V-1 验证 Agent"""
    try:
        from services.ai_agent_service import call_agent
        return call_agent("V-1", context)
    except Exception as e:
        logger.error(f"Failed to call verifier agent: {e}")
        return {
            "verdict": "failed",
            "dimensions": {
                "business_result": {"status": "error", "details": f"调用失败: {str(e)}"},
                "cross_task_consistency": {"status": "error", "details": f"调用失败: {str(e)}"},
                "goal_alignment": {"status": "error", "details": f"调用失败: {str(e)}"},
                "quality": {"status": "error", "details": f"调用失败: {str(e)}"},
            },
            "feedback": f"验证 Agent 调用失败: {str(e)}",
        }


def _parse_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """解析 V-1 Agent 返回结果"""
    dimensions = raw.get("dimensions", {})
    for dim in ["business_result", "cross_task_consistency", "goal_alignment", "quality"]:
        if dim not in dimensions:
            dimensions[dim] = {"status": "passed", "details": "未检测到，自动通过"}
    
    passed = [d.get("status") == "passed" for d in dimensions.values()]
    all_passed = all(passed) if passed else False
    partial_passed = any(passed) if passed else False
    
    return {
        "verdict": "passed" if all_passed else ("partial" if partial_passed else "failed"),
        "dimensions": dimensions,
        "feedback": raw.get("feedback", ""),
    }


def _write_result(task_id: str, result: Dict[str, Any], db) -> bool:
    """写入验证结果到 DB"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return False
        
        # 存储四维度结果到 result_summary（JSON 格式）
        task.result_summary = json.dumps(result, ensure_ascii=False)
        task.updated_at = int(__import__('datetime').datetime.utcnow().timestamp())
        
        if result.get("verdict") == "passed":
            task.status = "done"
        else:
            task.status = "review_needed"
            task.error_message = result.get("feedback", "验证未通过")
        
        task.verification_cycle = (task.verification_cycle or 0) + 1
        db.commit()
        
        logger.info(f"Verification result written for task {task_id}: {result.get('verdict')}")
        return True
    except Exception as e:
        logger.error(f"Failed to write verification result for task {task_id}: {e}")
        return False


async def four_dimension_verify(task: Task, verifier_agent_id: str, db_manager=None, verification_round: int = 0) -> Dict[str, Any]:
    """
    四维度验证入口
    
    Args:
        task: 任务对象
        verifier_agent_id: 验证者 Agent ID
        db_manager: 数据库管理器
        verification_round: 当前验证轮次（从 1 开始）
        
    Returns:
        验证结果字典
    """
    db = db_manager or get_db_manager()
    session = db.get_session()
    
    try:
        # 获取同 project 任务和 goal
        project_tasks = session.query(Task)\
            .filter(Task.project_id == task.project_id)\
            .filter(Task.id != task.id)\
            .all() if task.project_id else []
        
        goal = session.query(Goal).filter(Goal.id == task.goal_id).first() if task.goal_id else None
    finally:
        session.close()
    
    # 构建上下文并调用（传入 verification_round）
    context = _build_context(task, project_tasks, goal, verification_round)
    raw_result = await _call_verifier_agent(context)
    parsed = _parse_result(raw_result)
    
    parsed["raw_result"] = raw_result
    parsed["verification_round"] = verification_round
    return parsed


def run_full_validation(task_id: str, db_manager=None, verification_round: int = 0) -> Dict[str, Any]:
    """
    运行完整的四维度验证流程
    
    Args:
        task_id: 任务 ID
        db_manager: 数据库管理器
        verification_round: 当前验证轮次（从 1 开始）
        
    Returns:
        验证结果
    """
    db = db_manager or get_db_manager()
    session = db.get_session()
    
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        # 运行四维度验证
        result = asyncio.run(four_dimension_verify(task, "V-1", db, verification_round))
        
        # 写入 DB
        _write_result(task_id, result, db)
        
        return result
        
    finally:
        session.close()
