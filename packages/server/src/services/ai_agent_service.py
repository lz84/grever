# -*- coding: utf-8 -*-
"""AI Agent 统一交互服务 — prompt_library + call_agent 统一入口

职责（文档 23 号 9.9 节）：
1. DB 集中管理 prompt 模板（prompt_library 表）
2. 统一 AI 交互服务（call_agent 函数）

调用方式：
- planning 类交互 → Coordinator Session
- 其他交互 → OpenClaw CLI sessions_spawn
"""
import json
from typing import Any, Dict, Optional

from loguru import logger

from services._ai_agent_templates import get_prompt_template, update_prompt_template, list_prompt_templates
from services._ai_agent_renderer import validate_context, render_prompt
from services._ai_agent_caller import call_planning_agent, call_openclaw_cli
from services._ai_agent_parser import parse_json_response
from services._ai_agent_logger import log_interaction


def call_agent(interaction_id: str, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """调用 Agent 进行交互的统一入口。

    Args:
        interaction_id: 交互编号，如 E-1, E-3, SR-1, V-1, DP-1, KF-1
        context: 上下文变量字典（会按 context_schema 校验）
        **kwargs: 额外参数，如 session_id, timeout_seconds, model

    Returns:
        Agent 的响应结果（解析后的 JSON）

    Raises:
        ValueError: 如果 context 不符合 schema 或 prompt 不活跃
        RuntimeError: 如果调用失败
    """
    prompt_template = get_prompt_template(interaction_id)
    if not prompt_template:
        raise ValueError(f"Prompt template not found or not active: {interaction_id}")

    validate_context(context, prompt_template.get("context_schema"))
    rendered_prompt = render_prompt(prompt_template.get("content", ""), context)

    category = prompt_template.get("category", "")
    try:
        if category == "planning":
            result = call_planning_agent(rendered_prompt, prompt_template, context, **kwargs)
        else:
            result = call_openclaw_cli(rendered_prompt, category, interaction_id, **kwargs)
    except Exception as e:
        logger.error(f"[call_agent] Agent call failed for {interaction_id}: {e}")
        raise RuntimeError(f"Agent call failed: {e}")

    parsed_result = parse_json_response(result, prompt_template.get("output_schema"))
    log_interaction(interaction_id, prompt_template.get("version"), context, parsed_result)
    return parsed_result


# ============================================================================
# Convenience Functions (per interaction type)
# ============================================================================

def evaluate_decomposition(
    goal_id: str, goal_title: str, goal_description: str,
    coordinator_agent_id: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """E-1: 评估目标是否准备好分解"""
    context = {"goal_id": goal_id, "goal_title": goal_title, "goal_description": goal_description}
    if coordinator_agent_id:
        context["coordinator_agent_id"] = coordinator_agent_id
    return call_agent("E-1", context, **kwargs)


def submit_hitl_answers(goal_id: str, answers: Dict[str, str], **kwargs) -> Dict[str, Any]:
    """E-3: 提交 HITL 问答答案"""
    return call_agent("E-3", {"goal_id": goal_id, "answers": json.dumps(answers, ensure_ascii=False)}, **kwargs)


def verify_task(
    task_id: str, task_title: str, result_summary: str,
    acceptance_criteria: str, context_md: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """V-1: 验证任务结果"""
    context = {
        "task_id": task_id, "task_title": task_title,
        "result_summary": result_summary, "acceptance_criteria": acceptance_criteria,
    }
    if context_md:
        context["context_md"] = context_md
    return call_agent("V-1", context, **kwargs)


def dispatch_task(
    task_id: str, task_title: str,
    failure_reason: Optional[str] = None, previous_result: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """DP-1: 派发任务给 Agent"""
    context = {"task_id": task_id, "task_title": task_title}
    if failure_reason:
        context["failure_reason"] = failure_reason
    if previous_result:
        context["previous_result"] = previous_result
    return call_agent("DP-1", context, **kwargs)


def self_review_task(
    task_id: str, task_title: str, context_md: str,
    process_standards: Optional[list] = None, **kwargs
) -> Dict[str, Any]:
    """SR-1: 任务自检"""
    context = {"task_id": task_id, "task_title": task_title, "context_md": context_md}
    if process_standards:
        context["process_standards"] = "\n".join(f"- {s}" for s in process_standards[:10])
    return call_agent("SR-1", context, **kwargs)
