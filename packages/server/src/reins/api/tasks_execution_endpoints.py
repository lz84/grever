"""Task API complete_task endpoint — extracted from tasks.py

Contains only the complete_task endpoint (POST /{task_id}/complete) which is ~550 lines.
Uses helpers from tasks_execution_core.py.
"""
from loguru import logger
import json
import uuid
import threading
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.task import Task
from models.goal import Goal
from models.project import Project
from models.agent import Agent
from models.solution import Solution
from reins.common.database import get_db
from reins.scheduler.statemachine import transition_task_status
from reins.scheduler.result_verifier import ResultVerifier

from reins.api.tasks_models import CompleteTaskRequest, CompleteTaskResponse
from reins.api.tasks_execution_core import (
    _write_execution_log,
    _handle_human_input,
    _handle_scenario_feedback,
    _handle_agent_load_on_complete,
    _auto_complete_project,
    _publish_task_completed_event,
    _sprint74_capture_and_compare,
)
from reins.api.tasks_helpers import _get_goal_id_from_project, _update_goal_progress

# ── Evo 蒸馏触发计数器（动态路径）────────────────────────────────────────
_DISTILL_COUNTER_FILE = str(Path(__file__).resolve().parents[5] / "data" / "distill_counter.txt")
_DISTILL_TRIGGER_THRESHOLD = 10  # 每完成 10 个任务触发一次蒸馏
_DISTILL_LOOKBACK_DAYS = 90

_distill_lock = threading.Lock()

def _maybe_trigger_distillation():
    """
    任务完成后检查蒸馏计数器，每 10 个任务触发一次 Evo 蒸馏。
    失败不阻断任务完成流程（try/except 包裹）。
    """
    try:
        with _distill_lock:
            counter = 0
            try:
                with open(_DISTILL_COUNTER_FILE, "r") as f:
                    counter = int(f.read().strip())
            except (FileNotFoundError, ValueError):
                counter = 0

            counter += 1

            if counter >= _DISTILL_TRIGGER_THRESHOLD:
                counter = 0  # 重置计数器
                logger.info(f"[Evo] Distillation triggered after task completion (counter reached {_DISTILL_TRIGGER_THRESHOLD})")
                try:
                    from evo.trigger_distill import run_distillation
                    result = run_distillation(lookback_days=_DISTILL_LOOKBACK_DAYS)
                    logger.info(f"[Evo] Distillation completed: {result}")
                except Exception as e:
                    logger.error(f"[Evo] Distillation failed: {e}", exc_info=True)

            with open(_DISTILL_COUNTER_FILE, "w") as f:
                f.write(str(counter))
            logger.debug(f"[Evo] Distillation counter: {counter}/{_DISTILL_TRIGGER_THRESHOLD}")
    except Exception as e:
        # 计数器写入失败也不阻断任务完成
        logger.error(f"[Evo] Counter update failed: {e}", exc_info=True)

router = APIRouter(tags=["tasks"])

@router.post("/{task_id}/complete", response_model=CompleteTaskResponse)
def complete_task(task_id: str, request: CompleteTaskRequest, db: Session = Depends(get_db)):
    """
    MAK-215: 任务完成 API(P1: 必须传入执行证据)

    Updates task status, triggers scenario library feedback, updates Goal progress.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # ---- P1 校验: 执行证据 ----
    if not request.result or len(request.result) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_result",
                "message": "result 必须至少 5 个字符,用于描述执行结果",
                "received": request.result,
            }
        )

    if not request.execution_log or not isinstance(request.execution_log, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_execution_log",
                "message": "execution_log 必须是非空字典,提供执行过程证据",
                "received": request.execution_log,
            }
        )

    if request.duration_ms <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_duration_ms",
                "message": "duration_ms 必须 > 0,防止假报",
                "received": request.duration_ms,
            }
        )

    # ── Bug Fix: 完成任务前必须检查 depends_on ──────────────────────────────
    if request.status == "done":
        dep_ids = task.depends_on or []
        if dep_ids and isinstance(dep_ids, str):
            try:
                dep_ids = json.loads(dep_ids)
            except Exception:
                dep_ids = []
        if dep_ids:
            dep_check = db.query(Task.id, Task.status).filter(Task.id.in_(dep_ids)).all()
            undone = [(rid, rstatus) for rid, rstatus in dep_check if rstatus != "done"]
            if undone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "dependencies_not_met",
                        "message": f"任务的依赖尚未全部完成，无法标记 done",
                        "undone_dependencies": [{"id": rid, "status": rstatus} for rid, rstatus in undone],
                        "how_to_fix": "请先完成依赖任务，或等待调度器自动完成后再试",
                    }
                )

    # ── Sprint 91: 缺少 acceptance_criteria 时自动生成 fallback，不直接拒绝 ──
    has_acceptance_criteria = bool(task.acceptance_criteria and task.acceptance_criteria.strip())
    if not has_acceptance_criteria:
        logger.warning(
            f"[complete_task] Task {task_id} missing acceptance_criteria, auto-generating fallback"
        )
        fallback_criteria = json.dumps({
            "criteria": [
                {"type": "output", "name": "执行输出", "desc": f"任务执行完成: {request.result[:100]}"}
            ]
        }, ensure_ascii=False)
        task.acceptance_criteria = fallback_criteria
        db.add(task)
        # 延迟 commit，与后续操作一起提交

    # ── Sprint 86d-1: 完成时必须填写 context_md（需要验证的任务） ──────────────
    has_context_md = bool(task.context_md and task.context_md.strip())
    if has_acceptance_criteria and not has_context_md:
        # 有验收标准但没有 context_md → 需要验证的任务缺少施工记录
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "context_md_required",
                "message": "需要验证的任务完成时必须填写 context_md（执行者施工记录）。"
                           "请通过 PUT /api/v1/tasks/{id} 设置 context_md 后再完成。",
                "how_to_fix": 'PUT /api/v1/tasks/{id} body={"context_md": "## 执行概要\\n[做了什么]\\n\\n## 修改文件\\n- 文件: 改动\\n\\n## 验证步骤\\n1. 命令 -> 结果\\n\\n## 注意事项\\n无"}',
            }
        )

    old_status = task.status
    validation_passed = True
    validation_reason = ""

    if request.status == "done":
        from services.task_validator import validate_task_result
        validation_passed, validation_reason = validate_task_result(task, request.result)

        if not validation_passed:
            transition_task_status(
                db, task, "review_needed",
                reason=f"Task completed: review_needed, validation: failed - {validation_reason}",
                extra={"result_summary": validation_reason},
            )
        elif task.acceptance_criteria and task.acceptance_criteria.strip():
            # 【Sprint 91 修复】needs_verification=True 但无 verifier_agent_id → 自动禁用过验证
            if task.needs_verification and not task.verifier_agent_id:
                logger.warning(
                    f"[complete_task] Task {task_id}: needs_verification=True but no verifier_agent_id, "
                    f"auto-disabling verification and completing as done"
                )
                task.needs_verification = False
                db.add(task)
                transition_task_status(
                    db, task, "done",
                    reason=f"Task completed: done (verification auto-disabled: no verifier assigned)",
                    extra={"result_summary": request.result},
                )
                _write_execution_log(task, request, db)
                _handle_human_input(task, request, old_status, db)
                goal_progress = None
                task_goal_id = _get_goal_id_from_project(db, task.project_id)
                if task_goal_id:
                    goal_progress = _update_goal_progress(db, task_goal_id)
                    if goal_progress:
                        db.commit()
                        goal = db.query(Goal).filter(Goal.id == task_goal_id).first()
                        if goal:
                            db.refresh(goal)
                if task.project_id and task.status == "done":
                    _auto_complete_project(db, task)
                scenario_feedback_triggered = False
                scenario_evolution_result = None
                if getattr(task, 'category', None) and task.status == "done":
                    scenario_feedback_triggered, scenario_evolution_result = _handle_scenario_feedback(task, request, db)
                _handle_agent_load_on_complete(task, db)
                db.commit()
                db.refresh(task)
                if task.status == "done":
                    _publish_task_completed_event(task, task_goal_id, request, validation_passed, validation_reason)
                if task_goal_id:
                    goal_mode = db.query(Goal).filter(Goal.id == task_goal_id).first()
                    if goal_mode and getattr(goal_mode, 'mode', None) == "research":
                        _sprint74_capture_and_compare(db, task, request, task_goal_id)
                _maybe_trigger_distillation()
                return CompleteTaskResponse(
                    success=True,
                    task_id=task_id,
                    goal_progress=goal_progress,
                    scenario_feedback_triggered=scenario_feedback_triggered,
                    scenario_evolution_result=scenario_evolution_result,
                )
            transition_task_status(
                db, task, "verifying",
                reason=f"Task completed: verifying",
                extra={
                    "result_summary": request.result + " [等待 verifier agent 验证]",
                    "result": request.result,
                },
            )
            db.commit()

            verifier = ResultVerifier()
            verify_result = verifier.trigger_verification(task_id, request.result, True, task.context_md)

            if verify_result["passed"]:
                transition_task_status(
                    db, task, "done",
                    reason=f"Task completed: done, auto-verify passed",
                    extra={"result_summary": request.result, "result": request.result},
                )
            elif verify_result["action"] == "disputed":
                transition_task_status(
                    db, task, "disputed",
                    reason=f"Task completed: disputed by auto-verify",
                    extra={"result_summary": request.result},
                )
            else:
                transition_task_status(
                    db, task, "review_needed",
                    reason=f"Task completed: review_needed by auto-verify",
                    extra={"result_summary": request.result},
                )

            task_goal_id = _get_goal_id_from_project(db, task.project_id)
            logger.info(f"[Sprint 74] Auto-capture (verifying path): task_id={task_id}, task_goal_id={task_goal_id}")
            if task_goal_id and verify_result.get("passed"):
                _sprint74_capture_and_compare(db, task, request, task_goal_id)

            return CompleteTaskResponse(success=True, task_id=task_id)
        else:
            transition_task_status(
                db, task, "done",
                reason=f"Task completed: done",
            )
    else:
        transition_task_status(
            db, task, request.status,
            reason=f"Task completed: {request.status}",
            extra={"result_summary": request.result} if request.status == "done" else None,
        )

    _write_execution_log(task, request, db)
    _handle_human_input(task, request, old_status, db)

    goal_progress = None
    task_goal_id = _get_goal_id_from_project(db, task.project_id)
    if task_goal_id:
        goal_progress = _update_goal_progress(db, task_goal_id)
        if goal_progress:
            db.commit()
            goal = db.query(Goal).filter(Goal.id == task_goal_id).first()
            if goal:
                db.refresh(goal)

    if task.project_id and task.status == "done":
        _auto_complete_project(db, task)

    scenario_feedback_triggered = False
    scenario_evolution_result = None
    if getattr(task, 'category', None) and task.status == "done":
        scenario_feedback_triggered, scenario_evolution_result = _handle_scenario_feedback(task, request, db)

    _handle_agent_load_on_complete(task, db)

    db.commit()
    db.refresh(task)

    if task.status == "done":
        _publish_task_completed_event(task, task_goal_id, request, validation_passed, validation_reason)

    if task_goal_id:
        goal_mode = db.query(Goal).filter(Goal.id == task_goal_id).first()
        if goal_mode and getattr(goal_mode, 'mode', None) == "research":
            _sprint74_capture_and_compare(db, task, request, task_goal_id)

    # ── Evo 蒸馏触发：每完成 10 个任务触发一次 ─────────────────────
    _maybe_trigger_distillation()

    return CompleteTaskResponse(
        success=True,
        task_id=task_id,
        goal_progress=goal_progress,
        scenario_feedback_triggered=scenario_feedback_triggered,
        scenario_evolution_result=scenario_evolution_result,
    )