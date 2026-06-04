"""Security Audit Module"""
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """审计操作类型"""
    TASK_CREATE = "task_create"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    GOAL_CREATE = "goal_create"
    PROJECT_CREATE = "project_create"
    AGENT_REGISTER = "agent_register"
    AGENT_UNREGISTER = "agent_unregister"
    VERIFICATION_TRIGGER = "verification_trigger"
    VERIFICATION_PASS = "verification_pass"
    VERIFICATION_FAIL = "verification_fail"
    HITL_REQUEST = "hitl_request"
    HITL_APPROVE = "hitl_approve"
    HITL_REJECT = "hitl_reject"


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db_manager=None):
        self._db = db_manager
    
    def log(self, action: AuditAction, actor: str, target: str, details: dict = None):
        """记录审计日志"""
        _write_audit_log(action=action.value if isinstance(action, AuditAction) else action,
                        actor=actor, target=target, details=details or {})
    
    def get_logs(self, actor: str = None, action: str = None, limit: int = 100):
        """查询审计日志"""
        return []


_db_manager = None

def set_db_manager(db_manager):
    """设置数据库管理器"""
    global _db_manager
    _db_manager = db_manager


def _write_audit_log(action: str, actor: str, target: str, details: dict = None):
    """内部写审计日志"""
    if _db_manager is None:
        logger.info(f"[AUDIT] {action} by {actor} on {target}: {details}")
    else:
        # TODO: write to DB
        logger.debug(f"[AUDIT] {action} by {actor} on {target}: {details}")


def audit_log(action: str, actor: str, target: str, details: dict = None):
    """审计日志入口函数"""
    _write_audit_log(action=action, actor=actor, target=target, details=details)


def audit_task_create(task_id: str, operator: str = "system", details: dict = None):
    """审计任务创建"""
    audit_log(action="task_create", actor=operator, target=task_id, details=details)


def audit_task_complete(task_id: str, operator: str = "system", details: dict = None):
    """审计任务完成"""
    audit_log(action="task_complete", actor=operator, target=task_id, details=details)


def audit_task_fail(task_id: str, operator: str = "system", details: dict = None):
    """审计任务失败"""
    audit_log(action="task_fail", actor=operator, target=task_id, details=details)


def audit_goal_create(goal_id: str, operator: str = "system", details: dict = None):
    """审计目标创建"""
    audit_log(action="goal_create", actor=operator, target=goal_id, details=details)


def audit_project_create(project_id: str, operator: str = "system", details: dict = None):
    """审计项目创建"""
    audit_log(action="project_create", actor=operator, target=project_id, details=details)


def audit_agent_register(agent_id: str, operator: str = "system", details: dict = None):
    """审计智能体注册"""
    audit_log(action="agent_register", actor=operator, target=agent_id, details=details)


def audit_agent_unregister(agent_id: str, operator: str = "system", details: dict = None):
    """审计智能体注销"""
    audit_log(action="agent_unregister", actor=operator, target=agent_id, details=details)
