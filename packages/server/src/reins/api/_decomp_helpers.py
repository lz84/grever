# -*- coding: utf-8 -*-
"""Decomposition Router — 辅助函数"""
import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from loguru import logger


def _build_e1_context(goal, planning_session, db) -> Dict[str, Any]:
    """从 goal + planning_session 构建 E-1 评估上下文"""
    from models.scenario import Scenario
    industry_pack_context = {}
    if goal.matched_scenario_id:
        scenario = db.query(Scenario).filter(Scenario.id == goal.matched_scenario_id).first()
        if scenario:
            industry_pack_context = {"scenario_id": scenario.id, "scenario_name": getattr(scenario, "name", ""),
                                     "template_dag": getattr(scenario, "template_dag", None)}
    return {"goal_id": goal.id, "goal_title": goal.title or "", "goal_description": goal.description or "",
            "industry_pack_context": industry_pack_context,
            "system_defaults": {"priority_default": "medium", "category_default": "other"},
            "planning_context": _build_planning_context(planning_session)}


def _build_planning_context(planning_session) -> Dict[str, Any]:
    """从 planning_session.discussion_log 构建规划上下文"""
    discussion = []
    if planning_session.discussion_log:
        try:
            discussion = json.loads(planning_session.discussion_log)
        except (json.JSONDecodeError, TypeError):
            discussion = []
    confirmed_plan = None
    if planning_session.confirmed_plan:
        try:
            confirmed_plan = json.loads(planning_session.confirmed_plan)
        except (json.JSONDecodeError, TypeError):
            confirmed_plan = planning_session.confirmed_plan
    return {
        "session_id": planning_session.id, "status": planning_session.status,
        "discussion": discussion, "confirmed_plan": confirmed_plan,
    }


def _extract_previous_questions(discussion: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从 discussion_log 中提取所有未回答的 Tier 0 问题"""
    questions = []
    answered_ids = set()
    for entry in discussion:
        if entry.get("role") == "user" and entry.get("type") == "hitl_answers":
            try:
                answers = json.loads(entry.get("content", "{}"))
                answered_ids.update(answers.keys())
            except (json.JSONDecodeError, TypeError):
                pass
    for entry in discussion:
        if entry.get("role") == "agent" and "tier0_questions" in entry:
            for q in entry.get("tier0_questions", []):
                qid = q.get("question_id", "")
                if qid not in answered_ids:
                    questions.append(q)
    return questions


def _llm_fallback_decomposition(context: Dict[str, Any], interaction: str) -> Dict[str, Any]:
    """当 Coordinator Session 不可用时的降级 LLM 调用（E-1/E-3）"""
    import os
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("BAILIAN_API_KEY", "")
    api_base = os.environ.get("OPENAI_API_BASE") or os.environ.get("BAILIAN_API_BASE", "")
    model = os.environ.get("OPENAI_MODEL") or os.environ.get("BAILIAN_MODEL", "bailian/qwen3-coder-next")
    if not api_key:
        logger.warning("[_llm_fallback] No API key found")
        return {"assessment": "insufficient", "questions": [], "message": "No LLM API key configured"}
    if not api_base:
        api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    goal_title = context.get("goal_title", "")
    goal_description = context.get("goal_description", "")
    if interaction == "E-1":
        prompt = f"""你是一个项目规划助手。请评估以下 Goal 是否可以分解为 Projects 和 Tasks。

Goal 标题：{goal_title}
Goal 描述：{goal_description}

如果可以分解，输出：{{"assessment": "sufficient", "projects": [{{"name": "项目名称", "description": "描述", "category": "other", "tasks": [{{"title": "任务名称", "description": "", "priority": "medium"}}]}}], "assumptions": []}}

如果信息不足，输出：{{"assessment": "insufficient", "questions": [{{"id": "q1", "question": "问题内容", "reason": "需要澄清", "options": [{{"label": "A", "value": "选项A"}}, {{"label": "B", "value": "选项B"}}]}}], "assumptions_if_not_confirmed": []}}

请直接输出 JSON，不要有其他文字。"""
    else:
        prev_q = context.get("previous_questions", "[]")
        answers = context.get("user_answers", "{}")
        prompt = f"""你是一个项目规划助手。

Goal 标题：{goal_title}
Goal 描述：{goal_description}

之前的问题：{prev_q}
用户回答：{answers}

如果可以分解，输出：{{"assessment": "sufficient", "projects": [...], "assumptions": []}}
如果仍不足，输出：{{"assessment": "insufficient", "questions": [...], "assumptions_if_not_confirmed": []}}

请直接输出 JSON。"""
    try:
        req = urllib.request.Request(
            f"{api_base}/chat/completions",
            data=json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                           "temperature": 0.3, "max_tokens": 2000}).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                logger.info(f"[_llm_fallback] {interaction}: assessment={parsed.get('assessment')}")
                return parsed
            logger.warning(f"[_llm_fallback] {interaction}: no JSON found")
            return {"assessment": "insufficient", "questions": [], "message": f"无法解析响应: {content[:200]}"}
    except Exception as e:
        logger.error(f"[_llm_fallback] {interaction}: {e}")
        return {"assessment": "insufficient", "questions": [], "message": f"LLM 调用失败: {e}"}


def _trigger_task_assigner(goal_id: str) -> None:
    """触发 TaskAssigner 分配待处理任务"""
    try:
        from reins.scheduler.task_assigner import TaskAssigner
        TaskAssigner().assign_pending_tasks()
    except Exception as e:
        logger.warning(f"[_trigger_task_assigner] Failed for goal_id={goal_id}: {e}")
