"""
Goal 状态机转换逻辑
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .goal import Goal, GoalStatus
# from .manager import GoalManager

class GoalStateMachine:
    """
    Goal 状态机
    实现状态转换规则:
    - draft → planned → in_progress → completed
    - in_progress → failed
    - failed → planned (重新规划)
    
    注意: 状态值使用字符串，与数据库和 API 保持一致
    """

    # 允许的状态转换 (使用字符串值)
    ALLOWED_TRANSITIONS = {
        'draft': ['planned'],
        'planned': ['in_progress'],
        'in_progress': ['completed', 'failed'],
        'completed': [],  # 完成后无后续转换
        'failed': ['planned'],
    }

    @staticmethod
    def can_transition(current, target) -> bool:
        """
        检查是否允许状态转换

        Args:
            current: 当前状态 (字符串或 GoalStatus)
            target: 目标状态 (字符串或 GoalStatus)

        Returns:
            bool: 是否允许转换
        """
        # 统一转为字符串
        current_str = str(current) if not isinstance(current, str) else current
        target_str = str(target) if not isinstance(target, str) else target
        allowed = GoalStateMachine.ALLOWED_TRANSITIONS.get(current_str, [])
        return target_str in allowed

    @staticmethod
    def validate_transition(current, target) -> bool:
        """
        验证状态转换，非法转换抛出异常

        Args:
            current: 当前状态 (字符串或 GoalStatus)
            target: 目标状态 (字符串或 GoalStatus)

        Raises:
            ValueError: 非法状态转换
        """
        current_str = str(current) if not isinstance(current, str) else current
        target_str = str(target) if not isinstance(target, str) else target
        
        if not GoalStateMachine.can_transition(current_str, target_str):
            raise ValueError(
                f"Invalid status transition: {current_str} → {target_str}. "
                f"Allowed: {GoalStateMachine.ALLOWED_TRANSITIONS.get(current_str, [])}"
            )
        return True

def update_goal_status(
    db: Session,
    goal_id: str,
    new_status: str,
    validate_only: bool = False
) -> Optional[Goal]:
    """
    更新 Goal 状态

    Args:
        db: 数据库会话
        goal_id: Goal ID
        new_status: 新状态
        validate_only: 是否仅验证转换，不实际更新

    Returns:
        Goal: 更新后的 Goal 对象（如果更新成功）
        None: Goal 不存在或转换失败

    Raises:
        ValueError: 非法状态转换
    """
    try:
        # 查询 Goal
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return None

        current_status = goal.status  # 直接使用字符串

        # 验证转换 (需要使用字符串值)
        GoalStateMachine.validate_transition(current_status, new_status)

        if validate_only:
            return goal

        # 更新状态
        old_status = goal.status
        new_status_str = str(new_status) if not isinstance(new_status, str) else new_status
        goal.status = new_status_str  # 直接使用字符串
        goal.updated_at = __import__('datetime').datetime.utcnow()

        # 如果完成，记录完成时间
        if new_status_str == 'completed':
            goal.completed_at = __import__('datetime').datetime.utcnow()
        elif new_status_str == 'failed':
            goal.failed_at = __import__('datetime').datetime.utcnow()
        elif new_status_str == 'planned' and old_status == 'failed':
            # failed → planned (重新规划)，清除失败时间
            goal.failed_at = None

        db.commit()
        db.refresh(goal)
        return goal

    except SQLAlchemyError as e:
        db.rollback()
        raise ValueError(f"Database error: {str(e)}")
    except ValueError:
        db.rollback()
        raise

def check_goal_completion(db: Session, goal_id: str) -> bool:
    """
    检查 Goal 是否完成

    完成条件:
    - 所有 child goals completed
    - 所有关联 tasks done

    Args:
        db: 数据库会话
        goal_id: Goal ID

    Returns:
        bool: 是否完成
    """
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return False

        # 检查子 goals
        child_goals = db.query(Goal).filter(Goal.parent_id == goal_id).all()
        for child in child_goals:
            if child.status != 'completed':
                return False

        # 检查关联 tasks (通过 goal_id 关联)
        from .models import Task
        tasks = db.query(Task).filter(Task.goal_id == goal_id).all()
        for task in tasks:
            if task.status not in ['done', 'completed']:
                return False

        return True

    except SQLAlchemyError:
        return False

def check_goal_failure(db: Session, goal_id: str) -> bool:
    """
    检查 Goal 是否失败

    失败条件:
    - 有 Task failed 且无替代路径

    Args:
        db: 数据库会话
        goal_id: Goal ID

    Returns:
        bool: 是否失败
    """
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return False

        # 检查关联 tasks
        from .models import Task
        tasks = db.query(Task).filter(Task.goal_id == goal_id).all()
        
        # 检查是否有失败的任务
        for task in tasks:
            if task.status == 'failed':
                # 检查是否有替代路径 (通过依赖关系)
                # 这里简化处理：只要有失败任务就标记 goal 为 failed
                # 实际应检查是否有其他并行路径可以继续
                return True

        return False

    except SQLAlchemyError:
        return False

def auto_update_workflow_status(db: Session, goal_id: str):
    """
    Goal 状态变更时自动更新关联 Workflow 状态

    Args:
        db: 数据库会话
        goal_id: Goal ID
    """
    from shared.database.session import get_database_manager
    from persistence.tables import workflows
    
    try:
        # 获取关联的 workflow (通过 goal_id)
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            return

        # 查询关联的 workflows (需要通过 goals 表的关联关系)
        # 由于 goals 表没有 direct workflow_id 外键，需要通过 goals 表的 goal_id 字段
        
        # 简化：直接查询 workflows 表中 goal_id 等于当前 goal_id 的记录
        workflow = db.execute(
            workflows.select().where(workflows.c.goal_id == goal_id)
        ).first()

        if workflow:
            # 根据 goal 状态更新 workflow 状态
            new_status = 'completed'
            if goal.status == 'in_progress':
                new_status = 'running'
            elif goal.status == 'failed':
                new_status = 'failed'
            elif goal.status == 'planned':
                new_status = 'draft'

            if new_status != workflow.status:
                db.execute(
                    workflows.update()
                    .where(workflows.c.id == workflow.id)
                    .values(status=new_status, updated_at=__import__('datetime').datetime.utcnow())
                )
                db.commit()

    except SQLAlchemyError:
        db.rollback()
