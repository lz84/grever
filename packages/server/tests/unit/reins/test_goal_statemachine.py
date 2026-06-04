"""
测试 Goal 状态机
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.goal import Goal, GoalStatus
from models.goal_statemachine import (
    GoalStateMachine,
    update_goal_status,
)


@pytest.fixture
def db_session():
    """创建测试数据库和 session"""
    # 使用内存数据库
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # 创建 goals 表
    from models.goal import Goal
    Goal.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_allowed_transitions():
    """测试允许的状态转换"""
    # draft → planned
    assert GoalStateMachine.can_transition(GoalStatus.DRAFT, GoalStatus.PLANNED) is True
    
    # planned → in_progress
    assert GoalStateMachine.can_transition(GoalStatus.PLANNED, GoalStatus.IN_PROGRESS) is True
    
    # in_progress → completed
    assert GoalStateMachine.can_transition(GoalStatus.IN_PROGRESS, GoalStatus.COMPLETED) is True
    
    # in_progress → failed
    assert GoalStateMachine.can_transition(GoalStatus.IN_PROGRESS, GoalStatus.FAILED) is True
    
    # failed → planned
    assert GoalStateMachine.can_transition(GoalStatus.FAILED, GoalStatus.PLANNED) is True


def test_invalid_transitions():
    """测试非法的状态转换"""
    # draft → in_progress (不允许，必须经过 planned)
    assert GoalStateMachine.can_transition(GoalStatus.DRAFT, GoalStatus.IN_PROGRESS) is False
    
    # completed → any (不允许)
    assert GoalStateMachine.can_transition(GoalStatus.COMPLETED, GoalStatus.PLANNED) is False
    
    # planned → draft (不允许)
    assert GoalStateMachine.can_transition(GoalStatus.PLANNED, GoalStatus.DRAFT) is False


def test_validate_transition_valid(db_session):
    """测试验证合法转换"""
    goal = Goal(
        id="goal-001",
        title="Test Goal",
        description="Test",
        status=GoalStatus.DRAFT,
    )
    
    db_session.add(goal)
    db_session.commit()
    
    # 验证转换
    result = GoalStateMachine.validate_transition(
        GoalStatus.DRAFT,
        GoalStatus.PLANNED
    )
    
    assert result is True


def test_validate_transition_invalid(db_session):
    """测试验证非法转换"""
    goal = Goal(
        id="goal-002",
        title="Test Goal",
        description="Test",
        status=GoalStatus.DRAFT,
    )
    
    db_session.add(goal)
    db_session.commit()
    
    # 验证非法转换
    with pytest.raises(ValueError):
        GoalStateMachine.validate_transition(
            GoalStatus.DRAFT,
            GoalStatus.COMPLETED  # draft → completed 不允许
        )


def test_update_goal_status_success(db_session):
    """测试更新 Goal 状态成功"""
    goal = Goal(
        id="goal-003",
        title="Test Goal",
        description="Test",
        status=GoalStatus.DRAFT,
    )
    
    db_session.add(goal)
    db_session.commit()
    
    # 更新状态
    updated = update_goal_status(
        db_session,
        "goal-003",
        GoalStatus.PLANNED
    )
    
    assert updated is not None
    assert updated.status == GoalStatus.PLANNED


def test_update_goal_status_invalid(db_session):
    """测试更新 Goal 状态失败（非法转换）"""
    goal = Goal(
        id="goal-004",
        title="Test Goal",
        description="Test",
        status=GoalStatus.DRAFT,
    )
    
    db_session.add(goal)
    db_session.commit()
    
    # 尝试非法转换
    with pytest.raises(ValueError):
        update_goal_status(
            db_session,
            "goal-004",
            GoalStatus.COMPLETED  # draft → completed 不允许
        )


def test_goal_with_timestamps(db_session):
    """测试 Goal 时间戳"""
    goal = Goal(
        id="goal-005",
        title="Test Goal",
        description="Test",
        status=GoalStatus.DRAFT,
    )
    
    db_session.add(goal)
    db_session.commit()
    
    assert goal.created_at is not None
    assert goal.updated_at is not None
    
    # 更新状态
    updated = update_goal_status(
        db_session,
        "goal-005",
        GoalStatus.PLANNED
    )
    
    assert updated.status == GoalStatus.PLANNED
