"""
验证仲裁逻辑 — 争议升级与自动修复

职责：
1. 连续失败升级 → disputed
2. 创建 dispute 记录
3. 自动修复循环 → redispatch 回 executor
4. 发送飞书通知
"""

import json
import uuid
from datetime import datetime
from typing import Dict

from loguru import logger

from reins.scheduler.statemachine import TaskStateMachine
from reins.scheduler.statemachine import ProjectStateMachine
from models import Task, Goal, Project, Agent, Dispute
from models.human_input import HumanInputRequest
from .reporter import (
    write_verification_comment,
    write_redispatch_comment,
    get_latest_verification_comment,
    send_feishu_notification,
)


def handle_disputed(
    db, task_id, verifier, cycle, message, checks, max_cycles, goal_id=None, assigned_agent=None
) -> Dict:
    """
    验证连续失败 → 升级为 disputed，转人工裁决。
    创建 dispute 记录，发送飞书通知。
    """
    from reins.scheduler.dependency_resolver import DependencyResolver

    comment_id = write_verification_comment(
        db, task_id, verifier, max_cycles, None,
        f"WARNING: {max_cycles} consecutive verification failures. Escalating to human ruling.",
        checks,
        max_cycles,
    )

    send_feishu_notification(db, task_id, message)

    dispute_id = f"disp-{uuid.uuid4().hex[:8]}"
    involved = [assigned_agent] if assigned_agent else []
    now = datetime.utcnow()

    # 更新任务状态（通过状态机）
    fsm = TaskStateMachine(db, task_id)
    extra = {
        "error_message": message,
        "verification_cycle": max_cycles,
        "ruling_comment_id": comment_id,
        "updated_at": now,
    }
    fsm.transition("disputed", reason="验证连续失败，升级为 disputed", extra=extra)

    # 更新目标进度
    _update_goal_progress(db, goal_id)

    # 写入 disputes 表
    db.add(Dispute(
        id=dispute_id,
        dispute_type="verification_failed",
        description=f"验证连续 {max_cycles} 次失败，需人工裁决。\n\n{message}",
        involved_agents=json.dumps(involved, ensure_ascii=False),
        related_task_id=task_id,
        goal_id=goal_id,
        raised_by_agent=verifier,
        status="open",
        created_at=now,
        updated_at=now,
        deadline=now,
    ))

    # 创建 HumanInputRequest 用于四循环闭环
    hir_id = f"hir-{uuid.uuid4().hex[:8]}"
    hir = HumanInputRequest(
        id=hir_id,
        task_id=task_id,
        goal_id=goal_id,
        scope="task",
        request_type="ruling",
        title=f"任务 {task_id} 验证连续失败，需人工裁决",
        description=f"验证连续 {max_cycles} 次失败。\n\n{message}",
        timeout_action="escalate",
        timeout_minutes=1440,
        branches_raw=json.dumps({
            "options": [
                {"value": "approve_task", "label": "任务通过，标记 done"},
                {"value": "redispatch", "label": "打回重做"},
                {"value": "cancel_task", "label": "取消任务"}
            ]
        }, ensure_ascii=False),
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(hir)

    db.commit()

    logger.info(f"[VerificationArbitration] Task {task_id} disputed after {max_cycles} failed cycles, dispute {dispute_id} created")
    return {
        "task_id": task_id,
        "passed": False,
        "action": "disputed",
        "verifier_agent": verifier,
        "unlocked_tasks": [],
        "verification_cycle": max_cycles,
    }


def handle_review_needed(
    db, task_id, verifier, cycle, message, checks, max_cycles, assigned_agent=None, goal_id=None
) -> Dict:
    """
    cycle < max_cycles → review_needed, 自动派发回原 Executor。
    """
    comment_id = write_verification_comment(
        db, task_id, verifier, cycle, False, message, checks, max_cycles
    )
    now = datetime.utcnow()

    # 更新任务状态（通过状态机）
    fsm = TaskStateMachine(db, task_id)
    extra = {
        "error_message": message,
        "verification_cycle": cycle,
        "ruling_comment_id": comment_id,
        "updated_at": now,
    }
    fsm.transition("review_needed", reason="验证失败，需重新评审", extra=extra)
    _update_goal_progress(db, goal_id)
    db.commit()

    latest_comment = get_latest_verification_comment(db, task_id)

    redispatch_info = None
    if assigned_agent:
        redispatch_info = redispatch_to_executor(db, task_id, assigned_agent, latest_comment)

    logger.info(
        f"[VerificationArbitration] Task {task_id} review_needed (cycle {cycle}/{max_cycles}), "
        f"redispatched to {assigned_agent}" if assigned_agent else "no executor to redispatch"
    )
    return {
        "task_id": task_id,
        "passed": False,
        "action": "review_needed",
        "verifier_agent": verifier,
        "unlocked_tasks": [],
        "verification_cycle": cycle,
        "redispatched_to": assigned_agent,
        "redispatch_info": redispatch_info,
    }


def handle_verification_passed(
    db, task_id, verifier, cycle, message, checks, max_cycles, assigned_agent=None, goal_id=None, project_id=None
) -> Dict:
    """
    全部通过 → done, 解锁依赖, 更新进度。
    """
    from reins.scheduler.dependency_resolver import DependencyResolver

    comment_id = write_verification_comment(
        db, task_id, verifier, cycle, True, message, checks, max_cycles
    )
    now = datetime.utcnow()

    # 减少 agent 当前任务数
    if assigned_agent:
        agent = db.query(Agent).filter(Agent.id == assigned_agent).first()
        if agent and agent.current_tasks:
            agent.current_tasks = max(0, agent.current_tasks - 1)
            agent.updated_at = now

    # 更新任务状态（通过状态机）
    extra = {
        "completed_at": now,
        "verification_cycle": cycle,
        "ruling_comment_id": comment_id,
        "updated_at": now,
    }
    fsm = TaskStateMachine(db, task_id)
    fsm.transition("done", reason="验证通过", extra=extra)

    # 解锁依赖
    resolver = DependencyResolver(db)
    unlocked = resolver.unlock_on_completion(task_id)

    # 更新目标进度
    _update_goal_progress(db, goal_id)

    # 自动完成工程
    _check_auto_complete_project(db, project_id)

    db.commit()

    logger.info(f"[VerificationArbitration] Task {task_id} verification passed: done (cycle {cycle})")
    return {
        "task_id": task_id,
        "passed": True,
        "action": "done",
        "verifier_agent": verifier,
        "unlocked_tasks": unlocked,
        "verification_cycle": cycle,
    }


def handle_no_criteria(db, task_id, verifier, cycle, max_cycles) -> Dict:
    """
    无验收标准 → review_needed，不得自动通过。
    """
    from .reporter import write_verification_comment

    comment_id = write_verification_comment(
        db, task_id, verifier, cycle, False,
        "No acceptance criteria defined. Task cannot be verified without criteria.",
        max_cycles=max_cycles,
    )
    now = datetime.utcnow()

    # 更新任务状态（通过状态机）
    fsm = TaskStateMachine(db, task_id)
    extra = {
        "error_message": "No acceptance criteria defined",
        "verification_cycle": cycle,
        "ruling_comment_id": comment_id,
        "updated_at": now,
    }
    fsm.transition("review_needed", reason="缺少验收标准，需重新评审", extra=extra)
    db.commit()

    logger.warning(f"[VerificationArbitration] Task {task_id} rejected: no acceptance criteria → review_needed")
    return {
        "task_id": task_id,
        "passed": False,
        "action": "review_needed",
        "verifier_agent": verifier,
        "unlocked_tasks": [],
        "verification_cycle": cycle,
        "reason": "No acceptance criteria defined",
    }


def redispatch_to_executor(db, task_id: str, executor_id: str, verification_comment: str) -> Dict:
    """
    自动修复循环 — 派发回 Executor
    将 review_needed 任务重新派发给原 executor
    """
    try:
        # 使用状态机更新任务状态
        fsm = TaskStateMachine(db, task_id)
        extra = {
            "assigned_agent": executor_id,
            "error_message": None,
            "updated_at": datetime.utcnow(),
        }
        fsm.transition("todo", reason="redispatch 回 executor", extra=extra)
        db.commit()

        logger.info(f"[VerificationArbitration] Task {task_id} redispatched to executor {executor_id}")

        comment_id = write_redispatch_comment(db, task_id, executor_id, verification_comment)

        return {
            "success": True,
            "task_id": task_id,
            "executor_id": executor_id,
            "comment_id": comment_id,
            "verification_comment": verification_comment[:200] if verification_comment else "",
        }
    except Exception as e:
        logger.error(f"[VerificationArbitration] Failed to redispatch task {task_id}: {e}")
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e),
        }


def _update_goal_progress(db, goal_id: str) -> None:
    """任务状态变更后自动重算目标进度"""
    if not goal_id:
        return
    try:
        total = db.query(Task).filter(Task.goal_id == goal_id).count()
        if total == 0:
            return
        done = db.query(Task).filter(Task.goal_id == goal_id, Task.status == 'done').count()
        progress = done / total

        db.query(Goal).filter(Goal.id == goal_id).update({
            "progress": progress,
        })

        if progress >= 1.0:
            goal = db.query(Goal).filter(Goal.id == goal_id).first()
            if goal:
                # 通过状态机检查并更新状态
                from reins.scheduler.statemachine import GoalStateMachine
                fsm = GoalStateMachine(db, goal_id)
                if not fsm.can_transition("completed"):
                    # 如果不能直接转 completed，尝试先转 in_progress
                    fsm.transition("in_progress", reason="progress 100%，transition to in_progress")
                    fsm.transition("completed", reason="所有任务完成，progress=1.0")
                else:
                    fsm.transition("completed", reason="所有任务完成，progress=1.0")
                logger.info(f"[VerificationArbitration] Goal {goal_id}: auto-completed (progress={progress:.0%})")

        db.commit()
        logger.info(f"[VerificationArbitration] Goal {goal_id}: progress updated to {progress:.0%} ({done}/{total})")
    except Exception as e:
        logger.error(f"[VerificationArbitration] Failed to update goal progress for {goal_id}: {e}")


def _check_auto_complete_project(db, project_id: str) -> None:
    """检查工程是否所有任务都已完成，是则标记工程为 completed"""
    if not project_id:
        return
    try:
        total = db.query(Task).filter(Task.project_id == project_id).count()
        if total == 0:
            return
        done = db.query(Task).filter(Task.project_id == project_id, Task.status == 'done').count()
        if total == done:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project and project.status not in ("completed", "on_hold"):
                # 使用 ProjectStateMachine 迁移状态
                fsm = ProjectStateMachine(db, project_id)
                fsm.transition("completed", reason=f"所有 {done}/{total} 个任务均已完成")
                logger.info(f"[VerificationArbitration] Project {project_id}: auto-completed ({done}/{total})")

                goal_id = project.goal_id
                if goal_id:
                    next_proj = db.query(Project).filter(
                        Project.goal_id == goal_id,
                        Project.status == 'draft',
                    ).order_by(Project.created_at.asc()).first()
                    if next_proj:
                        # 使用 ProjectStateMachine 迁移状态
                        next_fsm = ProjectStateMachine(db, next_proj.id)
                        next_fsm.transition("active", reason="自动激活下一个 draft 项目")
                        next_proj.updated_at = datetime.utcnow()
                        logger.info(f"[VerificationArbitration] Project {next_proj.id}: auto-activated (next draft project)")
                db.commit()
    except Exception as e:
        logger.error(f"[VerificationArbitration] _check_auto_complete_project failed for {project_id}: {e}")