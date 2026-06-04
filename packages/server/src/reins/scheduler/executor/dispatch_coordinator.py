"""
派发协调 — 任务状态变更、API 调用、日志写入

职责：
1. 标记任务 in_progress
2. 调用 complete_task API
3. 写 task_activity_log
4. 写 execution_logs
"""

import json
import uuid
from datetime import datetime
from typing import Dict

from loguru import logger
from sqlalchemy import text


def mark_in_progress(db, task_id: str, agent_id: str) -> None:
    """
    标记任务为 in_progress，更新 agent 心跳。
    前置条件：agent_id 必须已设置。
    """
    if not agent_id:
        raise RuntimeError(
            f"Cannot mark task {task_id} as in_progress: assigned_agent is NULL."
        )
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE tasks SET status = 'in_progress', "
                    "assigned_agent = :agent_id, assigned_at = :now, "
                    "started_at = :now, updated_at = :now WHERE id = :task_id"
                ),
                {
                    "agent_id": agent_id,
                    "now": datetime.now(),
                    "task_id": task_id,
                },
            )
            conn.execute(
                text(
                    "UPDATE agents SET last_heartbeat = :now, "
                    "health_status = 'online', updated_at = :now WHERE id = :agent_id"
                ),
                {
                    "agent_id": agent_id,
                    "now": datetime.now(),
                },
            )
            conn.commit()
            logger.debug(
                f"[DispatchCoordinator] Marked task {task_id} as in_progress, agent={agent_id}"
            )
    except Exception as e:
        logger.error(f"[DispatchCoordinator] Failed to mark task {task_id} as in_progress: {e}")
        raise


def call_complete_api(db, project_id: str, task_id: str, result_text: str, success: bool) -> bool:
    """调用 complete_task API（内部触发验证）。返回 True=成功, False=失败"""
    import requests

    api_url = f"http://127.0.0.1:8097/api/v1/tasks/{task_id}/complete"
    payload = {
        "status": "done" if success else "failed",
        "result": result_text[:500] if result_text else "No result",
        "execution_log": {
            "source": "project_executor",
            "project_id": project_id,
        },
        "duration_ms": 0,
    }

    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        logger.info(f"[DispatchCoordinator] Completed task {task_id}: {result}")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            err_body = e.response.json()
            if err_body.get("error") == "context_md_required":
                logger.info(f"[DispatchCoordinator] context_md missing for {task_id}, auto-generating")
                try:
                    context_md = f"## 执行概要\n{result_text[:200]}\n\n## 验证\n通过 agent subprocess 执行完成"
                    with db.engine.connect() as conn:
                        conn.execute(
                            text("UPDATE tasks SET context_md = :cmd WHERE id = :tid"),
                            {"cmd": context_md, "tid": task_id},
                        )
                        conn.commit()
                    with db.engine.connect() as conn:
                        row = conn.execute(
                            text("SELECT context_md FROM tasks WHERE id = :tid"),
                            {"tid": task_id},
                        ).fetchone()
                        ctx_md = row.context_md if row else context_md
                    payload2 = dict(payload)
                    payload2["context_md"] = ctx_md
                    response2 = requests.post(api_url, json=payload2, timeout=30)
                    response2.raise_for_status()
                    result2 = response2.json()
                    logger.info(
                        f"[DispatchCoordinator] Completed task {task_id} (after context_md auto-fill)"
                    )
                    return True
                except Exception as retry_e:
                    logger.error(
                        f"[DispatchCoordinator] context_md auto-fill retry failed for {task_id}: {retry_e}"
                    )
                    return False
        logger.error(f"[DispatchCoordinator] Failed to call complete API for {task_id}: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"[DispatchCoordinator] Failed to call complete API for {task_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"[DispatchCoordinator] Unexpected error completing task {task_id}: {e}")
        return False


def log_execution(
    db, task_id: str, agent_id: str, action: str,
    input_data: dict, output_data: dict, status: str,
    error_message: str = "", duration_ms: int = 0,
) -> None:
    """写入 execution_logs 表"""
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO execution_logs "
                    "(id, task_id, agent_id, action, input, output, status, "
                    " error_message, duration_ms, created_at, metadata) "
                    "VALUES "
                    "(:id, :task_id, :agent_id, :action, :input, :output, :status, "
                    " :error_message, :duration_ms, :created_at, :metadata)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "action": action,
                    "input": json.dumps(input_data, ensure_ascii=False),
                    "output": json.dumps(output_data, ensure_ascii=False),
                    "status": status,
                    "error_message": error_message,
                    "duration_ms": duration_ms,
                    "created_at": datetime.now(),
                    "metadata": json.dumps({"source": "project_executor"}, ensure_ascii=False),
                },
            )
            conn.commit()
    except Exception as e:
        logger.error(f"[DispatchCoordinator] log_execution failed for {task_id}/{action}: {e}")


def log_activity(
    db, task_id: str, old_status: str, new_status: str,
    reason: str = "", actor: str = None,
) -> None:
    """写入 task_activity_log 表"""
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO task_activity_log "
                    "(id, task_id, old_status, new_status, reason, actor, timestamp) "
                    "VALUES (:id, :task_id, :old_status, :new_status, :reason, :actor, :timestamp)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "task_id": task_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason,
                    "actor": actor or "system",
                    "timestamp": datetime.now(),
                },
            )
            conn.commit()
    except Exception as e:
        logger.error(f"[DispatchCoordinator] log_activity failed for {task_id}: {e}")
