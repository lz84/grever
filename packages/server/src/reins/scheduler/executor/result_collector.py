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

from reins.scheduler.statemachine import TaskStateMachine
from .dispatch_coordinator import (
    call_complete_api,
    log_execution,
    log_activity,
)
from reins.common.config import MAX_RESULT_SUMMARY, MAX_RESULT_DETAIL


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
    from models.task import Task
    from models.goal import Goal
    session = db.get_session()
    try:
        _task = session.query(Task).filter(Task.id == task_id).first()
        _verifier_agent_id = _task.verifier_agent_id if _task else None
        _needs_verification = bool(_task.needs_verification) if _task else False
        _goal_id = _task.goal_id if _task else None

        _effective_verifier = _verifier_agent_id
        if not _effective_verifier and _goal_id:
            _goal = session.query(Goal).filter(Goal.id == _goal_id).first()
            _effective_verifier = _goal.verifier_agent_id if _goal else None
    finally:
        session.close()

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
    """降级：只写结果数据，不绕过验证。状态统一设为 review_needed。"""
    logger.warning(f"[ResultCollector] complete API failed, falling back to direct DB update for {task_id}")
    try:
        from sqlalchemy.orm import Session
        from models.task import Task
        from models.execution_log import ExecutionLog

        now = datetime.now()
        now_ts = int(now.timestamp())

        # 1. 获取任务信息（只读）
        session = db.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"[ResultCollector] Task {task_id} not found for fallback update")
                return

            old_status = task.status or "todo"
            needs_started_at = not task.started_at and old_status != "todo"
            agent_id = task.assigned_agent if task.assigned_agent else "unknown"
        finally:
            session.close()

        # 2. 使用状态机更新任务状态（自动写入 activity log）
        status_for_update = "review_needed"
        extra_data = {
            "result_summary": (result_text or "")[:MAX_RESULT_SUMMARY],
            "result": (result_data.get("output", "") if result_data else result_text or "")[:MAX_RESULT_DETAIL],
            "error_message": error_reason if not success and error_reason else ("" if success else "nonzero_exit"),
            "updated_at": now_ts,
        }
        if needs_started_at:
            extra_data["started_at"] = now_ts

        fsm = TaskStateMachine(db, task_id)
        fsm.transition(status_for_update, reason="fallback 路径", extra=extra_data)
        # 注意：TaskStateMachine.transition() 已自动写入 activity log

        # 3. 写入 execution log（补充记录）
        session = db.get_session()
        try:
            exec_log = ExecutionLog(
                id=str(uuid.uuid4()),
                task_id=task_id,
                agent_id=agent_id,
                action="task_complete" if success else "task_fail",
                input=json.dumps({}),
                output=json.dumps(
                    {"result_summary": (result_text or "")[:MAX_RESULT_SUMMARY], "exit_code": exit_code},
                    ensure_ascii=False,
                ),
                status="success" if success else "failed",
                error_message=error_reason if not success else "",
                duration_ms=1000,
                created_at=now,
                metadata_=json.dumps({"source": "result_collector_fallback"}, ensure_ascii=False),
            )
            session.add(exec_log)
            session.commit()
            logger.info(
                f"[ResultCollector] Fallback DB update for {task_id}: {old_status} → {status_for_update} "
                f"(started_at={'补填' if needs_started_at else '已有'})"
            )
        finally:
            session.close()
    except Exception as e:
        logger.error(f"[ResultCollector] Fallback DB update failed for {task_id}: {e}", exc_info=True)


def get_goal_id(db, project_id: str) -> Optional[str]:
    """获取项目关联的 goal_id"""
    try:
        from models.project import Project
        from sqlalchemy.orm import Session
        with Session(db.engine) as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            return project.goal_id if project else None
    except Exception as e:
        logger.warning(f"[ResultCollector] Failed to get goal_id: {e}")
        return None


def fallback_complete(db, task_id: str, result_text: str, success: bool) -> None:
    """降级：直接更新 DB（简化版）"""
    try:
        from models.task import Task
        from sqlalchemy.orm import Session
        from reins.common.config import MAX_RESULT_SUMMARY
        now = datetime.now()
        status = "done" if success else "failed"
        error_msg = "" if success else "Execution failed"
        with Session(db.engine) as session:
            session.query(Task).filter(Task.id == task_id).update({
                "status": status,
                "result_summary": result_text[:MAX_RESULT_SUMMARY] if result_text else "",
                "completed_at": now,
                "error_message": error_msg,
                "updated_at": now,
            })
            session.commit()
        logger.info(f"[ResultCollector] Fallback completed task {task_id}: success={success}")
    except Exception as e:
        logger.error(f"[ResultCollector] Failed to fallback complete task {task_id}: {e}")
