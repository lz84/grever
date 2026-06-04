"""
结果收集 — 读取任务执行结果、更新 DB、触发验证

职责：
1. 从进程捕获 stdout/stderr 输出
2. 写 result file
3. 更新 tasks 表
4. 写 task_activity_log + execution_logs
5. 调用 complete_task API 触发验证
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy import text

from .dispatch_coordinator import (
    call_complete_api,
    log_execution,
    log_activity,
)


async def collect_result(
    db, project_id: str, task_id: str, in_progress: Dict[str, Any]
) -> Dict[str, Any]:
    """
    读取任务执行结果，更新 DB，触发验证。
    
    逻辑：
    1. 优先读 result 文件
    2. 否则从进程捕获输出
    3. 确定最终状态
    4. 调用 complete API，失败则降级直接更新 DB
    """
    from .task_runner_compat import read_result, write_result_file

    success = False
    result_text = ""
    error_reason = ""
    exit_code = -1
    result_data = None

    # 1. 优先读 result 文件
    result_data = await read_result(task_id)
    if result_data:
        success = result_data.get("status") == "success"
        result_text = result_data.get("output", "") or result_data.get("summary", "")
        error_reason = "" if success else (result_data.get("error", "") or "result_file_error")
        logger.info(f"[ResultCollector] Task {task_id}: using existing result file (status={result_data.get('status')})")
    else:
        # 2. 从进程捕获
        if task_id in in_progress:
            process = in_progress[task_id]
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=600
                )
                output_text = stdout.decode("utf-8", errors="replace") if stdout else ""
                exit_code = process.returncode or 0
                result_data = write_result_file(task_id, output_text, exit_code)
                success = result_data.get("status") == "success"
                result_text = result_data.get("output", "") or result_data.get("summary", "")
                logger.info(
                    f"[ResultCollector] Task {task_id}: captured output, wrote result file"
                )
            except asyncio.TimeoutError:
                logger.error(f"[ResultCollector] Task {task_id}: process output timeout")
                process.kill()
                result_text = "任务超时（10分钟无输出）"
                error_reason = "process_timeout"
            except Exception as e:
                logger.error(f"[ResultCollector] Task {task_id}: failed to capture output: {e}")
                result_text = f"捕获输出失败: {e}"
                error_reason = "output_capture_error"
        else:
            result_text = "进程已丢失且无结果文件"
            error_reason = "process_lost"

    # 3. 确定最终状态
    with db.engine.connect() as _conn:
        _row = _conn.execute(
            text(
                "SELECT verifier_agent_id, needs_verification, goal_id "
                "FROM tasks WHERE id = :tid"
            ),
            {"tid": task_id},
        ).fetchone()
        _verifier_agent_id = _row.verifier_agent_id if _row else None
        _needs_verification = bool(_row.needs_verification) if _row else False
        _goal_id = _row.goal_id if _row else None

    _effective_verifier = _verifier_agent_id
    if not _effective_verifier and _goal_id:
        _goal_row = _conn.execute(
            text("SELECT verifier_agent_id FROM goals WHERE id = :gid"),
            {"gid": _goal_id},
        ).fetchone()
        _effective_verifier = _goal_row.verifier_agent_id if _goal_row else None

    if not success:
        final_status = "failed"
    elif _effective_verifier:
        final_status = "review_needed"
    elif _needs_verification:
        final_status = "review_needed"
    else:
        final_status = "done"

    activity_reason = error_reason if not success else (
        f"任务完成: {result_text[:80]}" if result_text else "任务完成"
    )

    # 4. 调用 complete API，失败则降级
    api_ok = call_complete_api(db, project_id, task_id, result_text, success)

    if not api_ok:
        _fallback_update(
            db, task_id, final_status, result_text, result_data,
            error_reason, exit_code, success, activity_reason,
        )
    else:
        logger.info(f"[ResultCollector] complete API succeeded for {task_id}")

    return {"task_id": task_id, "success": success}


def _fallback_update(
    db, task_id, final_status, result_text, result_data,
    error_reason, exit_code, success, activity_reason,
):
    """降级：直接更新 DB（跳过验证链路）"""
    logger.warning(f"[ResultCollector] complete API failed, falling back to direct DB update for {task_id}")
    try:
        now = datetime.now()
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE tasks SET status = :status, completed_at = :now, "
                    "result_summary = :result_summary, result = :result, "
                    "error_message = :error_message, updated_at = :now "
                    "WHERE id = :task_id"
                ),
                {
                    "task_id": task_id,
                    "status": final_status,
                    "result_summary": (result_text or "")[:500],
                    "result": (result_data.get("output", "") if result_data else result_text or "")[:2000],
                    "error_message": error_reason if not success and error_reason else ("" if success else "nonzero_exit"),
                    "now": now,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO task_activity_log "
                    "(id, task_id, old_status, new_status, reason, actor, timestamp) "
                    "VALUES (:id, :task_id, :old_status, :new_status, :reason, :actor, :timestamp)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "task_id": task_id,
                    "old_status": "in_progress",
                    "new_status": final_status,
                    "reason": activity_reason,
                    "actor": "system",
                    "timestamp": now,
                },
            )
            row = conn.execute(
                text("SELECT assigned_agent FROM tasks WHERE id=:tid"),
                {"tid": task_id},
            ).fetchone()
            agent_id = (row[0] if row else None) or "unknown"
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
                    "action": "task_complete" if success else "task_fail",
                    "input": json.dumps({}),
                    "output": json.dumps(
                        {"result_summary": (result_text or "")[:500], "exit_code": exit_code},
                        ensure_ascii=False,
                    ),
                    "status": "success" if success else "failed",
                    "error_message": error_reason if not success else "",
                    "duration_ms": 0,
                    "created_at": now,
                    "metadata": json.dumps({"source": "project_executor"}, ensure_ascii=False),
                },
            )
            conn.commit()
            logger.info(f"[ResultCollector] Fallback DB update for {task_id}: {final_status}")
    except Exception as e:
        logger.error(f"[ResultCollector] Fallback DB update failed for {task_id}: {e}")


def get_goal_id(db, project_id: str) -> Optional[str]:
    """获取项目关联的 goal_id"""
    try:
        with db.engine.connect() as conn:
            row = conn.execute(
                text("SELECT goal_id FROM projects WHERE id = :pid"),
                {"pid": project_id},
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.warning(f"[ResultCollector] Failed to get goal_id: {e}")
        return None


def fallback_complete(db, task_id: str, result_text: str, success: bool) -> None:
    """降级：直接更新 DB（简化版）"""
    try:
        with db.engine.connect() as conn:
            now = datetime.now()
            status = "done" if success else "failed"
            error_msg = "" if success else "Execution failed"
            conn.execute(
                text(
                    "UPDATE tasks SET status = :status, result_summary = :result, "
                    "completed_at = :now, error_message = :error, updated_at = :now "
                    "WHERE id = :task_id"
                ),
                {
                    "status": status,
                    "result": result_text[:500],
                    "now": now,
                    "task_id": task_id,
                    "error": error_msg,
                },
            )
            conn.commit()
            logger.info(f"[ResultCollector] Fallback completed task {task_id}: success={success}")
    except Exception as e:
        logger.error(f"[ResultCollector] Failed to fallback complete task {task_id}: {e}")
