"""Vigil Security Module"""

from vigil.trust.trust import TrustEvaluator
from vigil.common.audit import (
    audit_log, audit_task_create, audit_task_complete, audit_task_fail,
    audit_goal_create, audit_project_create, audit_agent_register,
    audit_agent_unregister, set_db_manager
)
from vigil.alerts.alerts import AlertEngine
from vigil.access.access import AccessController, require_role

__all__ = [
    "TrustEvaluator",
    "audit_log",
    "audit_task_create",
    "audit_task_complete",
    "audit_task_fail",
    "audit_goal_create",
    "audit_project_create",
    "audit_agent_register",
    "audit_agent_unregister",
    "set_db_manager",
    "AlertEngine",
    "AccessController",
    "require_role",
]
