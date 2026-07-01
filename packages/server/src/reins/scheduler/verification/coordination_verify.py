"""统筹验证 — coordination_verify.py

入口：trigger_coordination_verification(target_id, level)
- Project: 所有 Task done → 触发 Project 级统筹验证
- Goal: 所有 Project completed → 触发 Goal 级统筹验证
"""
import asyncio
from typing import Any, Dict

from loguru import logger
from reins.common.database import get_db_session

from reins.scheduler.verification._cv_context import collect_context
from reins.scheduler.verification._cv_cv1_agent import build_cv1_prompt, call_cv1_agent, parse_cv1_output
from reins.scheduler.verification._cv_remediation import (
    save_report, mark_completed, get_current_round, resolve_verifier,
    create_remedial_tasks, re_verify_after_remediation,
)


def trigger_coordination_verification(target_id: str, level: str) -> Dict[str, Any]:
    """触发 Project 或 Goal 级统筹验证（同步入口）。"""
    try:
        return asyncio.run(_async_trigger_verification(target_id, level))
    except Exception as e:
        logger.error(f"[CV] trigger failed: target={target_id}, level={level}, error={e}")
        return {"passed": False, "verdict": "failed", "report_id": None,
                "remedial_tasks": None, "message": f"统筹验证执行失败: {e}"}


async def _async_trigger_verification(target_id: str, level: str) -> Dict[str, Any]:
    """异步执行统筹验证。"""
    session = get_db_session()
    try:
        # Step 1: 收集上下文
        context = collect_context(target_id, level, session)
        if context is None:
            return {"passed": False, "verdict": "failed", "report_id": None,
                    "remedial_tasks": None, "message": f"Target not found: {target_id} ({level})"}

        # Step 2-3: 获取轮次 + 解析验证者
        current_round = get_current_round(target_id, level, session)
        verifier_id = resolve_verifier(target_id, level, session)

        # Step 4: 构建 prompt 并调用 CV-1 Agent
        prompt = build_cv1_prompt(target_id, level, context)
        raw_output = await call_cv1_agent(verifier_id, prompt)

        # Step 5: 解析结果
        parsed = parse_cv1_output(raw_output)

        # Step 6: 写入 Report
        report_id = save_report(target_id, level, verifier_id, current_round, parsed, prompt, session)

        # Step 7: 处理结果
        verdict = parsed.get("verdict", "failed")
        remedial_tasks = parsed.get("remedial_tasks", [])

        if verdict == "passed":
            mark_completed(target_id, level, session)
            return {"passed": True, "verdict": verdict, "report_id": report_id,
                    "remedial_tasks": None, "message": "统筹验证通过",
                    "gaps": parsed.get("gaps", []), "recommendations": parsed.get("recommendations", [])}

        return {"passed": False, "verdict": verdict, "report_id": report_id,
                "remedial_tasks": remedial_tasks,
                "message": parsed.get("summary", "统筹验证发现 gaps"),
                "gaps": parsed.get("gaps", []), "recommendations": parsed.get("recommendations", [])}
    finally:
        session.close()
