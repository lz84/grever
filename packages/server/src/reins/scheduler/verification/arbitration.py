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
from sqlalchemy import text

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

    with db.engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE tasks SET status = 'disputed', "
                "error_message = :error, verification_cycle = :cycle, "
                "ruling_comment_id = :comment_id, updated_at = :now "
                "WHERE id = :task_id"
            ),
            {
                "error": message,
                "cycle": max_cycles,
                "now": datetime.now(),
                "task_id": task_id,
                "comment_id": comment_id,
            },
        )

        # 更新目标进度
        _update_goal_progress(db, goal_id)

        # 写入 disputes 表
        conn.execute(
            text(
                "INSERT INTO disputes "
                "(id, dispute_type, description, involved_agents, related_task_id, goal_id, "
                " raised_by_agent, status, created_at, updated_at, deadline) "
                "VALUES (:id, :dtype, :desc, :agents, :task_id, :goal_id, "
                " :raised_by, 'open', :now, :now, :deadline)"
            ),
            {
                "id": dispute_id,
                "dtype": "verification_failed",
                "desc": f"验证连续 {max_cycles} 次失败，需人工裁决。\n\n{message}",
                "agents": json.dumps(involved, ensure_ascii=False),
                "task_id": task_id,
                "goal_id": goal_id,
                "raised_by": verifier,
                "now": datetime.now(),
                "deadline": datetime.now(),
            },
        )
        conn.commit()

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

    with db.engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE tasks SET status = 'review_needed', "
                "error_message = :error, verification_cycle = :cycle, "
                "ruling_comment_id = :comment_id, updated_at = :now "
                "WHERE id = :task_id"
            ),
            {
                "error": message,
                "cycle": cycle,
                "now": datetime.now(),
                "task_id": task_id,
                "comment_id": comment_id,
            },
        )
        _update_goal_progress(db, goal_id)
        conn.commit()

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

    with db.engine.connect() as conn:
        # 减少 agent 当前任务数
        if assigned_agent:
            conn.execute(
                text(
                    "UPDATE agents SET current_tasks = MAX(0, current_tasks - 1), updated_at = :now "
                    "WHERE id = :agent_id"
                ),
                {"agent_id": assigned_agent, "now": datetime.now()},
            )

        conn.execute(
            text(
                "UPDATE tasks SET status = 'done', completed_at = :now, "
                "verification_cycle = :cycle, ruling_comment_id = :comment_id, "
                "updated_at = :now WHERE id = :task_id"
            ),
            {
                "now": datetime.now(),
                "cycle": cycle,
                "task_id": task_id,
                "comment_id": comment_id,
            },
        )

        # 解锁依赖
        resolver = DependencyResolver(db)
        unlocked = resolver.unlock_on_completion(task_id)

        # 更新目标进度
        _update_goal_progress(db, goal_id)

        # 自动完成工程
        _check_auto_complete_project(db, project_id)

        conn.commit()

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

    with db.engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE tasks SET status = 'review_needed', "
                "error_message = 'No acceptance criteria defined', "
                "verification_cycle = :cycle, ruling_comment_id = :comment_id, "
                "updated_at = :now WHERE id = :task_id"
            ),
            {
                "now": datetime.now(),
                "cycle": cycle,
                "task_id": task_id,
                "comment_id": comment_id,
            },
        )
        conn.commit()

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
        with db.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE tasks SET "
                    "status = 'todo', assigned_agent = :executor, "
                    "error_message = NULL, updated_at = :now "
                    "WHERE id = :task_id"
                ),
                {
                    "executor": executor_id,
                    "now": datetime.now(),
                    "task_id": task_id,
                },
            )
            conn.commit()

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
        with db.engine.connect() as conn:
            total = conn.execute(
                text("SELECT COUNT(*) FROM tasks WHERE goal_id = :gid"),
                {"gid": goal_id},
            ).fetchone()[0]
            if total == 0:
                return
            done = conn.execute(
                text("SELECT COUNT(*) FROM tasks WHERE goal_id = :gid AND status = 'done'"),
                {"gid": goal_id},
            ).fetchone()[0]
            progress = done / total
            conn.execute(
                text("UPDATE goals SET progress = :progress WHERE id = :gid"),
                {"progress": progress, "gid": goal_id},
            )
            if progress >= 1.0:
                row = conn.execute(
                    text("SELECT status FROM goals WHERE id = :gid"),
                    {"gid": goal_id},
                ).fetchone()
                if row and row[0] != "completed":
                    conn.execute(
                        text(
                            "UPDATE goals SET status = 'completed', completed_at = :now WHERE id = :gid"
                        ),
                        {"now": datetime.now(), "gid": goal_id},
                    )
                    logger.info(f"[VerificationArbitration] Goal {goal_id}: auto-completed (progress={progress:.0%})")
            conn.commit()
            logger.info(f"[VerificationArbitration] Goal {goal_id}: progress updated to {progress:.0%} ({done}/{total})")
    except Exception as e:
        logger.error(f"[VerificationArbitration] Failed to update goal progress for {goal_id}: {e}")


def _check_auto_complete_project(db, project_id: str) -> None:
    """检查工程是否所有任务都已完成，是则标记工程为 completed"""
    if not project_id:
        return
    try:
        with db.engine.connect() as conn:
            total = conn.execute(
                text("SELECT COUNT(*) FROM tasks WHERE project_id = :pid"),
                {"pid": project_id},
            ).fetchone()[0]
            if total == 0:
                return
            done = conn.execute(
                text("SELECT COUNT(*) FROM tasks WHERE project_id = :pid AND status = 'done'"),
                {"pid": project_id},
            ).fetchone()[0]
            if total == done:
                cur = conn.execute(
                    text("SELECT status FROM projects WHERE id = :pid"),
                    {"pid": project_id},
                ).fetchone()
                if cur and cur[0] not in ("completed", "on_hold"):
                    conn.execute(
                        text(
                            "UPDATE projects SET status = 'completed', updated_at = :now WHERE id = :pid"
                        ),
                        {"now": datetime.now(), "pid": project_id},
                    )
                    logger.info(f"[VerificationArbitration] Project {project_id}: auto-completed ({done}/{total})")

                goal_id = conn.execute(
                    text("SELECT goal_id FROM projects WHERE id = :pid"),
                    {"pid": project_id},
                ).fetchone()
                if goal_id:
                    gid = goal_id[0]
                    next_proj = conn.execute(
                        text(
                            "SELECT id FROM projects WHERE goal_id = :gid AND status = 'draft' "
                            "ORDER BY created_at ASC LIMIT 1"
                        ),
                        {"gid": gid},
                    ).fetchone()
                    if next_proj:
                        npid = next_proj[0]
                        conn.execute(
                            text(
                                "UPDATE projects SET status = 'active', updated_at = :now WHERE id = :pid"
                            ),
                            {"now": datetime.now(), "pid": npid},
                        )
                        logger.info(f"[VerificationArbitration] Project {npid}: auto-activated (next draft project)")
    except Exception as e:
        logger.error(f"[VerificationArbitration] _check_auto_complete_project failed for {project_id}: {e}")
