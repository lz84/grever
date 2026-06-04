"""
Vigil - RBAC 访问控制 (Access)

基于角色的访问控制 (Role-Based Access Control)。

角色层级：
- admin: 系统管理员，完全权限
- operator: 运维人员，管理 Agent 和任务
- analyst: 分析师，只读 + 报告
- agent: 执行 Agent，受限操作
- viewer: 观察者，只读

权限模型：
  Resource:Action  (如 task:read, agent:write, config:admin)
"""

import functools
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """角色定义"""
    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    AGENT = "agent"
    VIEWER = "viewer"


class Permission(str, Enum):
    """权限定义 (Resource:Action)"""
    # Agent
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_DELETE = "agent:delete"
    AGENT_REGISTER = "agent:register"
    AGENT_UNREGISTER = "agent:unregister"

    # Task
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    TASK_EXECUTE = "task:execute"

    # Project
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"

    # Goal
    GOAL_READ = "goal:read"
    GOAL_WRITE = "goal:write"
    GOAL_DELETE = "goal:delete"
    GOAL_DECOMPOSE = "goal:decompose"

    # Config
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    CONFIG_ADMIN = "config:admin"

    # Security
    SECURITY_AUDIT = "security:audit"
    SECURITY_ALERT = "security:alert"
    SECURITY_ADMIN = "security:admin"

    # Report
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"


# 角色-权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # 所有权限

    Role.OPERATOR: {
        Permission.AGENT_READ,
        Permission.AGENT_WRITE,
        Permission.AGENT_REGISTER,
        Permission.AGENT_UNREGISTER,
        Permission.TASK_READ,
        Permission.TASK_WRITE,
        Permission.TASK_ASSIGN,
        Permission.TASK_EXECUTE,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.GOAL_READ,
        Permission.GOAL_WRITE,
        Permission.CONFIG_READ,
        Permission.SECURITY_AUDIT,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
    },

    Role.ANALYST: {
        Permission.AGENT_READ,
        Permission.TASK_READ,
        Permission.PROJECT_READ,
        Permission.GOAL_READ,
        Permission.CONFIG_READ,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
        Permission.SECURITY_AUDIT,
    },

    Role.AGENT: {
        Permission.TASK_READ,
        Permission.TASK_EXECUTE,
        Permission.AGENT_READ,  # 读取自身信息
        Permission.REPORT_READ,
    },

    Role.VIEWER: {
        Permission.TASK_READ,
        Permission.PROJECT_READ,
        Permission.GOAL_READ,
        Permission.AGENT_READ,
        Permission.REPORT_READ,
    },
}


@dataclass
class UserContext:
    """用户/Agent 上下文"""
    user_id: str
    role: Role
    agent_id: Optional[str] = None  # 如果是 Agent 调用
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """检查是否有指定权限"""
        allowed = ROLE_PERMISSIONS.get(self.role, set())
        return permission in allowed

    def has_any_permission(self, *permissions: Permission) -> bool:
        """检查是否有任一权限"""
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, *permissions: Permission) -> bool:
        """检查是否有全部权限"""
        return all(self.has_permission(p) for p in permissions)


class AccessController:
    """
    RBAC 访问控制器

    用法：
        ac = AccessController()
        ac.set_user_role("agent-1", Role.AGENT)

        if ac.check_permission(user_ctx, Permission.TASK_EXECUTE):
            ...
    """

    def __init__(self):
        # user_id -> Role
        self._roles: Dict[str, Role] = {}
        # agent_id -> user_id (Agent 到用户的映射)
        self._agent_mapping: Dict[str, str] = {}
        # 自定义角色-权限覆盖
        self._custom_permissions: Dict[Role, Set[Permission]] = {}

    def set_user_role(self, user_id: str, role: Role) -> None:
        """设置用户角色"""
        self._roles[user_id] = role
        logger.info("User %s role set to %s", user_id, role.value)

    def get_user_role(self, user_id: str) -> Optional[Role]:
        """获取用户角色"""
        return self._roles.get(user_id)

    def map_agent_to_user(self, agent_id: str, user_id: str) -> None:
        """映射 Agent 到用户"""
        self._agent_mapping[agent_id] = user_id

    def get_user_for_agent(self, agent_id: str) -> Optional[str]:
        return self._agent_mapping.get(agent_id)

    def create_context(self, user_id: str, agent_id: Optional[str] = None) -> Optional[UserContext]:
        """创建用户上下文"""
        role = self._roles.get(user_id)
        if not role:
            return None
        return UserContext(
            user_id=user_id,
            role=role,
            agent_id=agent_id,
        )

    def check_permission(self, ctx: UserContext, permission: Permission) -> bool:
        """检查权限"""
        # 检查自定义覆盖
        custom = self._custom_permissions.get(ctx.role)
        if custom is not None:
            return permission in custom
        # 检查默认映射
        return permission in ROLE_PERMISSIONS.get(ctx.role, set())

    def check_resource_access(
        self,
        ctx: UserContext,
        resource_type: str,
        resource_id: str,
        action: str = "read",
    ) -> bool:
        """
        检查资源级访问权限

        例如: check_resource_access(ctx, "task", "task-123", "write")
        """
        # 构造权限字符串
        perm_str = f"{resource_type}:{action}"
        try:
            perm = Permission(perm_str)
        except ValueError:
            logger.warning("Unknown permission: %s", perm_str)
            return False

        return self.check_permission(ctx, perm)

    def add_custom_permission(self, role: Role, permission: Permission) -> None:
        """为角色添加自定义权限"""
        if role not in self._custom_permissions:
            self._custom_permissions[role] = set(ROLE_PERMISSIONS.get(role, set()))
        self._custom_permissions[role].add(permission)

    def remove_custom_permission(self, role: Role, permission: Permission) -> None:
        """移除角色的自定义权限"""
        if role in self._custom_permissions:
            self._custom_permissions[role].discard(permission)

    def list_user_permissions(self, user_id: str) -> Set[Permission]:
        """列出用户所有权限"""
        role = self._roles.get(user_id)
        if not role:
            return set()
        if role in self._custom_permissions:
            return self._custom_permissions[role]
        return ROLE_PERMISSIONS.get(role, set())


# ---------- 装饰器 ----------

def require_role(*allowed_roles: Role):
    """
    装饰器：要求调用者具有指定角色之一。

    用法：
        @require_role(Role.ADMIN, Role.OPERATOR)
        def delete_agent(agent_id, ctx: UserContext):
            ...

    被装饰函数必须接受 ctx: UserContext 参数。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 寻找 UserContext 参数
            ctx = kwargs.get("ctx")
            if ctx is None:
                for arg in args:
                    if isinstance(arg, UserContext):
                        ctx = arg
                        break

            if ctx is None:
                raise PermissionError(
                    f"Permission check failed: no UserContext found for {func.__name__}"
                )

            if not isinstance(ctx, UserContext):
                raise PermissionError(
                    f"Permission check failed: ctx is not UserContext for {func.__name__}"
                )

            if ctx.role not in allowed_roles:
                raise PermissionError(
                    f"Permission denied: role={ctx.role.value} "
                    f"required={'|'.join(r.value for r in allowed_roles)} "
                    f"for {func.__name__}"
                )

            logger.debug(
                "Role check passed: %s has role %s for %s",
                ctx.user_id, ctx.role.value, func.__name__,
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(*permissions: Permission):
    """
    装饰器：要求调用者具有指定权限之一。

    用法：
        @require_permission(Permission.TASK_WRITE, Permission.TASK_ASSIGN)
        def assign_task(task_id, agent_id, ctx: UserContext):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ctx = kwargs.get("ctx")
            if ctx is None:
                for arg in args:
                    if isinstance(arg, UserContext):
                        ctx = arg
                        break

            if ctx is None:
                raise PermissionError(
                    f"Permission check failed: no UserContext found for {func.__name__}"
                )

            if not ctx.has_any_permission(*permissions):
                perm_names = ", ".join(p.value for p in permissions)
                raise PermissionError(
                    f"Permission denied: user {ctx.user_id} (role={ctx.role.value}) "
                    f"lacks required permissions: {perm_names}"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator
