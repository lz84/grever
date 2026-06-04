"""
验证报告生成 — Comment 写入与解析

职责：
1. 写入 verification comment
2. 写入 redispatch comment
3. 获取最新 verification comment
4. 解析 agent 响应
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger


def write_verification_comment(
    db, task_id, verifier, cycle, passed, detail, checks=None, max_cycles=3
) -> str:
    """Write a structured verification comment to task_comments table"""
    from sqlalchemy import text

    status_icon = "PASS" if passed else ("DISPUTED" if passed is None else "FAIL")
    body = f"{status_icon} Verification {'passed' if passed else ('failed' if passed is False else 'disputed')} (cycle {cycle}/{max_cycles})\n\n{detail}"

    comment_id = f"cmt-{uuid.uuid4().hex[:8]}"
    metadata = json.dumps({
        "verification_cycle": cycle,
        "passed": passed,
        "checks": checks or [],
    })

    with db.engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO task_comments "
                "(id, task_id, author, author_role, type, content, metadata, created_at) "
                "VALUES (:id, :task_id, :author, :author_role, :type, :content, :metadata, :created_at)"
            ),
            {
                "id": comment_id,
                "task_id": task_id,
                "author": verifier,
                "author_role": "verifier",
                "type": "verification_result",
                "content": body,
                "metadata": metadata,
                "created_at": datetime.now(),
            },
        )
        conn.commit()

    logger.info(
        f"[VerificationReporter] Written comment {comment_id} for task {task_id}, cycle={cycle}, passed={passed}"
    )
    return comment_id


def write_redispatch_comment(db, task_id: str, executor_id: str, verification_comment: str) -> str:
    """写入 redispatch 记录到 task_comments"""
    from sqlalchemy import text

    comment_id = f"cmt-{uuid.uuid4().hex[:8]}"
    content = (
        f"Auto-repair: Task redispatched to executor {executor_id} after verification failure.\n\n"
        f"Verification feedback:\n{verification_comment}"
    )
    metadata = json.dumps({
        "redispatch_to": executor_id,
        "verification_comment": verification_comment[:500],
    })

    with db.engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO task_comments "
                "(id, task_id, author, author_role, type, content, metadata, created_at) "
                "VALUES (:id, :task_id, :author, :author_role, :type, :content, :metadata, :created_at)"
            ),
            {
                "id": comment_id,
                "task_id": task_id,
                "author": "verifier",
                "author_role": "system",
                "type": "redispatch",
                "content": content,
                "metadata": metadata,
                "created_at": datetime.now(),
            },
        )
        conn.commit()

    return comment_id


def get_latest_verification_comment(db, task_id: str) -> str:
    """获取最近的 verification comment 内容"""
    from sqlalchemy import text

    with db.engine.connect() as conn:
        comment = conn.execute(
            text(
                "SELECT content FROM task_comments "
                "WHERE task_id = :task_id AND type = 'verification_result' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"task_id": task_id},
        ).fetchone()
        return comment.content if comment else ""


def parse_checks_detail(db, task_id: str, result: str) -> list:
    """Parse acceptance criteria into check details for comment metadata"""
    from sqlalchemy import text

    with db.engine.connect() as conn:
        task = conn.execute(
            text("SELECT acceptance_criteria FROM tasks WHERE id = :id"),
            {"id": task_id},
        ).fetchone()

    if not task or not task.acceptance_criteria:
        return []

    try:
        criteria = json.loads(task.acceptance_criteria)
    except json.JSONDecodeError:
        return []

    if isinstance(criteria, dict) and "criteria" in criteria:
        criteria = criteria["criteria"]
    if not isinstance(criteria, list):
        return []

    checks = []
    for c in criteria:
        checks.append({
            "name": c.get("name", c.get("type", "unknown")),
            "type": c.get("type", "unknown"),
            "passed": True,
            "detail": "",
        })
    return checks


def parse_agent_response(output: str, expected_checks: List[Dict]) -> List[Dict]:
    """Parse agent output to extract check results"""
    import re

    json_match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", output)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", output)
        json_str = json_match.group(0) if json_match else ""

    if json_str:
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                results = []
                for check in expected_checks:
                    name = check.get("name", check.get("type", "unknown"))
                    match = next(
                        (r for r in parsed if r.get("name", "").lower() == name.lower()),
                        None,
                    )
                    results.append({
                        "name": name,
                        "type": "subjective",
                        "passed": match.get("passed", False) if match else False,
                        "detail": match.get("detail", "No detail provided")
                        if match
                        else "Agent did not return result for this check",
                    })
                return results
        except json.JSONDecodeError:
            logger.warning("[VerificationReporter] Failed to parse agent JSON response")

    return [
        {
            "name": c.get("name", c.get("type", "unknown")),
            "type": "subjective",
            "passed": False,
            "detail": "Failed to parse agent response",
        }
        for c in expected_checks
    ]


def send_feishu_notification(db, task_id: str, error_message: str):
    """发送飞书通知 - 任务争议提醒"""
    from sqlalchemy import text

    try:
        with db.engine.connect() as conn:
            task = conn.execute(
                text("SELECT title, description FROM tasks WHERE id = :id"),
                {"id": task_id},
            ).fetchone()

        if not task:
            logger.error(f"[VerificationReporter] Failed to get task details for notification: {task_id}")
            return

        task_title = task.title or f"Task {task_id}"
        task_description = task.description or ""
        task_url = f"http://localhost:5173/coordination/tasks/{task_id}"

        feishu_message = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "red",
                    "title": {"content": "⚠️ 任务争议提醒", "tag": "plain_text"},
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**任务标题：** {task_title}\n**错误信息：** {error_message}",
                            "tag": "lark_md",
                        },
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": (
                                f"**任务描述：** {task_description[:100]}..."
                                if len(task_description) > 100
                                else f"**任务描述：** {task_description}"
                                if task_description
                                else ""
                            ),
                            "tag": "lark_md",
                        },
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"content": "查看任务详情", "tag": "plain_text"},
                                "url": task_url,
                                "type": "default",
                            }
                        ],
                    },
                ],
            },
        }

        webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("[VerificationReporter] FEISHU_WEBHOOK_URL not configured, skipping notification")
            return

        import requests
        response = requests.post(webhook_url, json=feishu_message, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("StatusCode") == 0:
                logger.info(f"[VerificationReporter] Feishu notification sent for task {task_id}")
            else:
                logger.error(f"[VerificationReporter] Feishu notification failed: {result.get('msg')}")
        else:
            logger.error(f"[VerificationReporter] Feishu notification HTTP error: {response.status_code}")
    except Exception as e:
        logger.error(f"[VerificationReporter] Failed to send Feishu notification: {e}")
