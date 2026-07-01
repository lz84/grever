from datetime import datetime
import uuid
from typing import Any

from loguru import logger


class StateTransitionError(Exception):
    """非法状态流转异常"""
    def __init__(self, entity_type: str, entity_id: str, current: str, target: str, allowed: list[str]):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.current = current
        self.target = target
        self.allowed = allowed
        super().__init__(
            f"[{entity_type}] 非法状态流转: {entity_id}: {current} → {target}, "
            f"允许: {allowed}"
        )


VALID_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    # ─── Task ───
    "task": {
        "todo":            ["in_progress"],
        "in_progress":     ["review_needed", "done", "paused", "failed", "waiting_human"],
        "review_needed":   ["in_progress", "done", "disputed"],
        "done":            [],
        "disputed":        [],
        "paused":          ["todo"],
        "failed":          ["todo"],
        "waiting_human":   ["todo", "in_progress", "done", "failed"],
    },
    # ─── Project ───
    "project": {
        "draft":      ["active"],
        "active":     ["completed", "paused", "on_hold"],
        "completed":  [],
        "paused":     ["active"],
        "on_hold":    ["active"],
    },
    # ─── Goal ───
    "goal": {
        "draft":       ["planned"],
        "planned":     ["in_progress"],
        "in_progress": ["completed", "failed", "paused"],
        "completed":   [],
        "failed":      ["planned"],
        "paused":      ["in_progress"],
    },
}


class BaseStateMachine:
    """状态机基类 — 子类只需定义 entity_type 和 model_class"""

    entity_type: str = ""       # "task" / "project" / "goal"
    model_class: Any = None     # ORM model class

    def __init__(self, db, entity_id: str):
        self.db = db
        self.entity_id = entity_id
        self.current_state = self._load_state()

    def _load_state(self) -> str:
        """从 DB 加载当前状态"""
        session = self.db.get_session()
        try:
            entity = session.query(self.model_class).filter(
                self.model_class.id == self.entity_id
            ).first()
            if not entity:
                raise ValueError(f"{self.entity_type} {self.entity_id} not found")
            return entity.status or self._default_state()
        finally:
            session.close()

    def _default_state(self) -> str:
        return "todo"

    def _after_transition(self, old_state: str, new_state: str):
        """
        子类可覆盖此 hook，在 transition 成功后执行副作用。
        例如：级联传播、自动完成检测等。
        """
        pass

    def can_transition(self, target: str) -> bool:
        allowed = VALID_TRANSITIONS[self.entity_type].get(self.current_state, [])
        return target in allowed

    def transition(self, target: str, reason: str = "", extra: dict = None) -> bool:
        """
        执行状态转移：校验 → 写 DB → 写 activity log。
        返回 True = 成功，False = 非法流转（记 warning 日志）
        """
        if not self.can_transition(target):
            allowed = VALID_TRANSITIONS[self.entity_type].get(self.current_state, [])
            logger.warning(
                f"[StateMachine] Illegal transition: {self.entity_type} "
                f"{self.entity_id}: {self.current_state} → {target}, allowed={allowed}"
            )
            return False

        session = self.db.get_session()
        try:
            old_state = self.current_state
            update_data = {"status": target, "updated_at": int(datetime.now().timestamp())}

            # 终态补 completed_at
            if target in ("done", "completed"):
                update_data["completed_at"] = datetime.now()

            if extra:
                update_data.update(extra)

            session.query(self.model_class).filter(
                self.model_class.id == self.entity_id
            ).update(update_data)

            # 写 activity log（仅 Task 有 activity log 表，Goal/Project 跳过）
            if self.entity_type == "task":
                from models.task_activity_log import TaskActivityLog
                session.add(TaskActivityLog(
                    id=str(uuid.uuid4()),
                    task_id=self.entity_id,
                    old_status=old_state,
                    new_status=target,
                    reason=reason or f"状态机流转: {old_state} → {target}",
                    actor="system",
                    timestamp=datetime.now(),
                ))

            session.commit()
            self.current_state = target

            logger.info(f"[StateMachine] {self.entity_type} {self.entity_id}: {old_state} → {target}")

            # ─── 级联传播 ───
            self._after_transition(old_state, target)

            return True

        except Exception as e:
            session.rollback()
            logger.error(f"[StateMachine] Transition failed for {self.entity_type} {self.entity_id}: {e}")
            return False
        finally:
            session.close()


from models.task import Task
from models.project import Project
from models.goal import Goal


class TaskStateMachine(BaseStateMachine):
    entity_type = "task"
    model_class = Task
    def _default_state(self) -> str: return "todo"

    def _after_transition(self, old_state, new_state):
        # Task done → 级联检查 Project/Goal 是否需要自动完成
        if new_state == "done":
            cascade = StateMachineCascade(self.db)
            cascaded = cascade.on_task_transition(self.entity_id, new_state)
            if cascaded:
                logger.info(f"[Cascade] Task {self.entity_id} → {cascaded}")


class ProjectStateMachine(BaseStateMachine):
    entity_type = "project"
    model_class = Project
    def _default_state(self) -> str: return "draft"

    def _after_transition(self, old_state, new_state):
        pass


class GoalStateMachine(BaseStateMachine):
    entity_type = "goal"
    model_class = Goal
    def _default_state(self) -> str: return "draft"

    def _after_transition(self, old_state, new_state):
        # Goal paused → 级联暂停所有子 Project 和 Task
        if new_state == "paused":
            cascade = StateMachineCascade(self.db)
            cascaded = cascade.on_goal_pause(self.entity_id)
            if cascaded:
                logger.info(f"[Cascade] Goal {self.entity_id} paused → {cascaded}")


class StateMachineCascade:
    """
    状态变更级联传播。
    在 transition() 之后被调用，检查是否需要触发父实体状态变更。
    """

    def __init__(self, db):
        self.db = db

    def on_task_transition(self, task_id: str, new_status: str) -> list[str]:
        """
        Task 状态变更后调用。
        如果 task 变成 done，检查关联 Project 是否全部 done → 触发 Project completed。
        返回变更的实体 ID 列表。
        """
        results = []
        if new_status != "done":
            return results

        session = self.db.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task or not task.project_id:
                return results

            # 检查 Project 下所有 Task 是否都 done
            all_done = session.query(Task).filter(
                Task.project_id == task.project_id,
                Task.status.notin_(["done", "failed", "completed"])
            ).count() == 0

            if all_done:
                fsm = ProjectStateMachine(self.db, task.project_id)
                if fsm.can_transition("completed"):
                    fsm.transition("completed", reason=f"所有子 Task 已完成，Project {task.project_id} 自动完成")
                    results.append(task.project_id)
                    # 递归检查 Goal
                    goal_result = self._check_goal_auto_complete(task.project_id)
                    results.extend(goal_result)
            return results
        finally:
            session.close()

    def _check_goal_auto_complete(self, project_id: str) -> list[str]:
        """Project completed 后，检查关联 Goal 是否全部 Project completed"""
        results = []
        session = self.db.get_session()
        try:
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project or not project.goal_id:
                return results

            all_done = session.query(Project).filter(
                Project.goal_id == project.goal_id,
                Project.status.notin_(["completed"])
            ).count() == 0

            if all_done:
                fsm = GoalStateMachine(self.db, project.goal_id)
                if fsm.can_transition("completed"):
                    fsm.transition("completed", reason=f"所有子 Project 已完成，Goal {project.goal_id} 自动完成")
                    results.append(project.goal_id)
            return results
        finally:
            session.close()

    def on_goal_pause(self, goal_id: str) -> list[str]:
        """
        Goal paused 后，所有子 Project paused，所有子 Task paused。
        """
        results = []
        session = self.db.get_session()
        try:
            projects = session.query(Project).filter(
                Project.goal_id == goal_id,
                Project.status.notin_(["completed"])
            ).all()
            for proj in projects:
                fsm = ProjectStateMachine(self.db, proj.id)
                if fsm.can_transition("paused"):
                    fsm.transition("paused", reason=f"Goal {goal_id} 已暂停")
                    results.append(proj.id)

                # Project 下的 Task 也暂停
                tasks = session.query(Task).filter(
                    Task.project_id == proj.id,
                    Task.status.notin_(["done", "failed", "completed"])
                ).all()
                for task in tasks:
                    tsm = TaskStateMachine(self.db, task.id)
                    if tsm.can_transition("paused"):
                        tsm.transition("paused", reason=f"Goal {goal_id} 已暂停")
            return results
        finally:
            session.close()


# ─── 兼容层（供 API 层 tasks_state.py 等直接调用） ───

from sqlalchemy.orm import Session as SASession
from typing import Optional


def transition_task_status(
    db: SASession,
    task: Task,
    new_status: str,
    reason: str = "",
    actor: Optional[str] = None,
    extra: Optional[dict] = None,
) -> Task:
    """
    兼容层：兼容旧 reins.common.task_statemachine 接口。
    透传给 TaskStateMachine.transition()。
    """
    ok = TaskStateMachine(db, task.id).transition(new_status, reason=reason, extra=extra)
    if not ok:
        # 重新加载最新状态
        db.refresh(task)
    return task


def batch_transition_task_status(
    db: SASession,
    tasks: list[Task],
    new_status: str,
    reason: str = "",
    actor: Optional[str] = None,
    extra: Optional[dict] = None,
) -> tuple[list[Task], list[dict]]:
    """
    兼容层：批量状态变更。
    """
    success = []
    failed = []
    for task in tasks:
        ok = TaskStateMachine(db, task.id).transition(new_status, reason=reason, extra=extra)
        if ok:
            success.append(task)
        else:
            failed.append({"task_id": task.id, "error": f"Invalid transition to {new_status}"})
    return success, failed


__all__ = ["StateTransitionError", "VALID_TRANSITIONS", "BaseStateMachine", "TaskStateMachine", "ProjectStateMachine", "GoalStateMachine", "StateMachineCascade", "transition_task_status", "batch_transition_task_status"]
