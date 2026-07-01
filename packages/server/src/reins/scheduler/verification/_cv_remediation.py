"""Coordination verification — report saving, remedial tasks, re-verification."""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from reins.common.database import get_db_session
from models.task import Task, TaskStatus
from models.project import Project
from models.goal import Goal
from models.verification_report import VerificationReport
from reins.scheduler.statemachine import ProjectStateMachine, GoalStateMachine

MAX_REMEDIATION_ROUNDS = 3



def _resolve_default_verifier():
    """Resolve default verifier UUID from system_config."""
    try:
        from shared.database.agent_resolver import get_default_verifier_id
        from reins.common.database import get_db_session
        with get_db_session() as session:
            return get_default_verifier_id(session)
    except Exception:
        return None

def save_report(
    target_id: str, level: str, verifier_id: str, round_num: int,
    parsed: Dict[str, Any], raw_context: str, session,
) -> str:
    """将验证结果写入 verification_reports 表。"""
    report_id = f"vr-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    report = VerificationReport(
        id=report_id, level=level, target_id=target_id, verifier_id=verifier_id,
        round=round_num, verdict=parsed.get("verdict", "failed"),
        summary=parsed.get("summary", ""),
        task_results=json.dumps(parsed.get("task_results", {}), ensure_ascii=False),
        gaps=json.dumps(parsed.get("gaps", []), ensure_ascii=False),
        recommendations=json.dumps(parsed.get("recommendations", []), ensure_ascii=False),
        remedial_tasks=json.dumps(parsed.get("remedial_tasks", []), ensure_ascii=False),
        raw_context=raw_context[:10000] if len(raw_context) > 10000 else raw_context,
        created_at=now,
    )
    session.add(report)
    session.commit()
    logger.info("[CV] Report saved: id=%s, target=%s, round=%d, verdict=%s",
                report_id, target_id, round_num, parsed.get("verdict"))
    return report_id


def mark_completed(target_id: str, level: str, session) -> None:
    """验证通过后更新 Project/Goal 状态。"""
    now_ts = int(datetime.utcnow().timestamp())
    if level == "project":
        project = session.query(Project).filter(Project.id == target_id).first()
        if project:
            # 通过状态机更新状态
            fsm = ProjectStateMachine(session, target_id)
            fsm.transition("completed", reason="CV mark completed", extra={"updated_at": now_ts})
            logger.info(f"[CV] Project {target_id} marked as completed")
    elif level == "goal":
        goal = session.query(Goal).filter(Goal.id == target_id).first()
        if goal:
            # 通过状态机更新状态
            fsm = GoalStateMachine(session, target_id)
            fsm.transition("completed", reason="CV mark completed", extra={
                "completed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                "progress": 1.0,
                "updated_at": now_ts
            })
            logger.info(f"[CV] Goal {target_id} marked as completed")
    session.commit()


def get_current_round(target_id: str, level: str, session) -> int:
    """查询当前最大 round。"""
    row = session.query(VerificationReport).filter(
        VerificationReport.target_id == target_id,
        VerificationReport.level == level,
    ).order_by(VerificationReport.round.desc()).first()
    return (row.round + 1) if row else 1


def resolve_verifier(target_id: str, level: str, session) -> str:
    """解析验证者 Agent ID（三级继承链）。"""
    if level == "project":
        project = session.query(Project).filter(Project.id == target_id).first()
        if project and getattr(project, "verifier_agent_id", None):
            return project.verifier_agent_id
        if project and project.goal_id:
            goal = session.query(Goal).filter(Goal.id == project.goal_id).first()
            if goal and getattr(goal, "verifier_agent_id", None):
                return goal.verifier_agent_id
    elif level == "goal":
        goal = session.query(Goal).filter(Goal.id == target_id).first()
        if goal and getattr(goal, "verifier_agent_id", None):
            return goal.verifier_agent_id
    return _resolve_default_verifier() or "3745f1f0-b67d-4287-a10b-e71b3ff17e97"


def create_remedial_tasks(
    goal_id: str, project_id: Optional[str], remedial_tasks: List[Dict[str, Any]],
) -> List[str]:
    """根据 remedial_tasks 建议创建新 Task。"""
    if not remedial_tasks:
        return []

    session = get_db_session()
    created_ids = []
    try:
        for rt in remedial_tasks:
            task_id = f"task-{uuid.uuid4().hex[:12]}"
            now_ts = int(datetime.utcnow().timestamp())
            capability_tags = rt.get("capability_tags", {})
            if isinstance(capability_tags, dict):
                capability_tags = json.dumps(capability_tags, ensure_ascii=False)
            elif not isinstance(capability_tags, str):
                capability_tags = "{}"
            priority = rt.get("priority", "medium")
            if priority not in ("low", "medium", "high"):
                priority = "medium"

            task = Task(
                id=task_id, title=rt.get("title", "补救任务"),
                description=rt.get("description", ""), status="todo",
                priority=priority, capability_tags=capability_tags,
                goal_id=goal_id, project_id=project_id or rt.get("project_id"),
                created_at=now_ts, updated_at=now_ts,
                needs_verification=True, verification_round=0, verification_cycle=0,
            )
            session.add(task)
            created_ids.append(task_id)

        session.commit()
        logger.info("[CV] Created %d remedial tasks for goal=%s", len(created_ids), goal_id)

        try:
            from reins.scheduler.task_assigner import TaskAssigner
            TaskAssigner().assign_pending_tasks()
        except Exception as e:
            logger.warning(f"[CV] assign_pending_tasks failed: {e}")

        return created_ids
    finally:
        session.close()


def re_verify_after_remediation(target_id: str, level: str, current_round: int) -> Dict[str, Any]:
    """补救 Task 全部 done 后再次触发统筹验证。"""
    if current_round >= MAX_REMEDIATION_ROUNDS:
        _trigger_hitl(target_id, level, current_round)
        return {"passed": False, "verdict": "failed", "report_id": None,
                "remedial_tasks": None, "message": f"超过最大复测轮次（{MAX_REMEDIATION_ROUNDS}），触发 HITL",
                "hitl": True}

    if not _all_remedial_tasks_done(target_id, level):
        return {"passed": False, "verdict": "pending", "report_id": None,
                "remedial_tasks": None, "message": "仍有补救 Task 未完成"}

    from reins.scheduler.verification.coordination_verify import trigger_coordination_verification
    return trigger_coordination_verification(target_id, level)


def _all_remedial_tasks_done(target_id: str, level: str) -> bool:
    """检查关联的补救 Task 是否全部 done。"""
    session = get_db_session()
    try:
        if level == "project":
            tasks = session.query(Task).filter(
                Task.project_id == target_id,
                Task.status.notin_([TaskStatus.TODO, TaskStatus.CANCELED]),
            ).all()
            return all(t.status == TaskStatus.DONE for t in tasks)
        elif level == "goal":
            projects = session.query(Project).filter(Project.goal_id == target_id).all()
            for p in projects:
                tasks = session.query(Task).filter(
                    Task.project_id == p.id,
                    Task.status.notin_([TaskStatus.TODO, TaskStatus.CANCELED]),
                ).all()
                if not all(t.status == TaskStatus.DONE for t in tasks):
                    return False
            return True
        return False
    finally:
        session.close()


def _trigger_hitl(target_id: str, level: str, round_num: int) -> None:
    """超过最大复测轮次，触发 HITL。"""
    from models import HumanInputRequest
    session = get_db_session()
    try:
        hir = HumanInputRequest(
            id=f"hir-cv-{uuid.uuid4().hex[:12]}", task_id=None,
            type="coordination_verification_dispute",
            prompt=(f"{level.capitalize()} {target_id} 在 {round_num} 轮统筹验证后仍存在 gaps，请人工审核并决策。"),
            status="pending", created_at=datetime.utcnow(),
        )
        session.add(hir)
        session.commit()
        logger.info(f"[CV] HITL triggered for {level} {target_id}")
    finally:
        session.close()
