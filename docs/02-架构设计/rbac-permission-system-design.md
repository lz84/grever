# Nexus RBAC 权限控制系统设计

> 版本: v1.0-draft | 日期: 2026-05-07 | 状态: 设计评审中

---

## 一、设计目标

| 目标 | 说明 |
|------|------|
| **RBAC 访问控制** | 用户-角色-权限三层模型，支持细粒度 API 级权限 |
| **数据权限** | 行级数据过滤，按组织/部门/个人维度控制可见范围 |
| **最小侵入** | 业务代码零改动或仅加装饰器，权限系统独立部署 |
| **可插拔** | 一个配置开关决定 Nexus 是否启用权限系统 |
| **DB 兼容** | 业务表预留权限字段，不开权限时不产生额外开销 |

---

## 二、总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Nexus 主系统                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Goals    │  │ Projects │  │ Tasks    │  │ Scenarios  │  │
│  │ API      │  │ API      │  │ API      │  │ API        │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       └──────────────┴──────────────┴──────────────┘         │
│                          │                                    │
│              ┌───────────▼───────────┐                        │
│              │   Permission Plugin   │ ← 配置开关 enabled:bool│
│              │  (middleware + decorator)                      │
│              └───────────┬───────────┘                        │
└──────────────────────────┼────────────────────────────────────┘
                           │ HTTP gRPC
              ┌────────────▼────────────┐
              │   Auth Service (独立)    │
              │  ┌───────────────────┐  │
              │  │ User Management   │  │
              │  │ Role Management   │  │
              │  │ Permission Engine │  │
              │  │ Data Filter       │  │
              │  └───────────────────┘  │
              │  SQLite / PostgreSQL    │
              └─────────────────────────┘
```

### 核心原则

1. **Auth Service 独立进程运行**，与 Nexus 主系统解耦
2. Nexus 通过 **middleware** 拦截请求 → 调用 Auth Service 校验 → 注入权限上下文
3. Auth Service 未启动 / `enabled=false` 时 → 旁路直通，不影响业务
4. 业务表增加 `created_by`, `org_id`, `dept_id` 等字段，**不开权限时这些字段为 NULL，查询不走额外过滤**

---

## 三、数据模型设计

### 3.1 Auth Service 数据库表

```sql
-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT    NOT NULL UNIQUE,           -- UUID
    username      TEXT    NOT NULL UNIQUE,           -- 登录名
    password_hash TEXT    NOT NULL,                  -- bcrypt
    display_name  TEXT,                              -- 显示名
    email         TEXT    UNIQUE,
    phone         TEXT    UNIQUE,
    org_id        INTEGER,                           -- 所属组织
    dept_id       INTEGER,                           -- 所属部门
    status        TEXT    NOT NULL DEFAULT 'active', -- active / disabled / locked
    last_login_at DATETIME,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 组织表（可选，多租户场景）
-- ============================================================
CREATE TABLE organizations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id        TEXT    NOT NULL UNIQUE,           -- UUID
    name          TEXT    NOT NULL,
    parent_id     INTEGER REFERENCES organizations(id),
    status        TEXT    NOT NULL DEFAULT 'active',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 部门表
-- ============================================================
CREATE TABLE departments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_id       TEXT    NOT NULL UNIQUE,           -- UUID
    org_id        INTEGER NOT NULL REFERENCES organizations(id),
    name          TEXT    NOT NULL,
    parent_id     INTEGER REFERENCES departments(id),
    status        TEXT    NOT NULL DEFAULT 'active',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 角色表
-- ============================================================
CREATE TABLE roles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id       TEXT    NOT NULL UNIQUE,           -- UUID
    name          TEXT    NOT NULL UNIQUE,           -- 角色名，如 admin, viewer, operator
    display_name  TEXT    NOT NULL,                  -- 显示名，如 系统管理员
    description   TEXT,
    org_id        INTEGER REFERENCES organizations(id), -- NULL = 全局角色
    role_type     TEXT    NOT NULL DEFAULT 'system', -- system(系统内置) / custom(自定义)
    status        TEXT    NOT NULL DEFAULT 'active',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 权限表（API 级 + 数据级）
-- ============================================================
CREATE TABLE permissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    perm_id       TEXT    NOT NULL UNIQUE,           -- UUID
    resource      TEXT    NOT NULL,                  -- 资源名，如 goal, project, task
    action        TEXT    NOT NULL,                  -- 操作，如 create, read, update, delete
    scope         TEXT    NOT NULL DEFAULT 'api',    -- api(接口级) / data(数据级)
    description   TEXT,
    UNIQUE(resource, action, scope)
);

-- ============================================================
-- 角色-权限关联表
-- ============================================================
CREATE TABLE role_permissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id       INTEGER NOT NULL REFERENCES roles(id),
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    UNIQUE(role_id, permission_id)
);

-- ============================================================
-- 用户-角色关联表（支持多角色）
-- ============================================================
CREATE TABLE user_roles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    role_id       INTEGER NOT NULL REFERENCES roles(id),
    assigned_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by   INTEGER REFERENCES users(id),      -- 分配人
    UNIQUE(user_id, role_id)
);

-- ============================================================
-- 数据权限规则表（行级过滤规则）
-- ============================================================
CREATE TABLE data_permission_rules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id       INTEGER NOT NULL REFERENCES roles(id),
    resource      TEXT    NOT NULL,                  -- 目标资源
    rule_type     TEXT    NOT NULL,                  -- self / dept / dept_and_children / org / all
    -- self: 只看自己创建的
    -- dept: 看本部门创建的
    -- dept_and_children: 看本部门及子部门创建的
    -- org: 看本组织创建的
    -- all: 看所有
    -- custom: 自定义 SQL 表达式
    custom_expr TEXT,                                -- rule_type=custom 时的 SQL 表达式
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, resource)
);

-- ============================================================
-- JWT Token 黑名单（可选，用于强制登出）
-- ============================================================
CREATE TABLE token_blacklist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    jti           TEXT    NOT NULL UNIQUE,           -- JWT ID
    expires_at    DATETIME NOT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 操作审计日志
-- ============================================================
CREATE TABLE audit_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT    NOT NULL,
    action        TEXT    NOT NULL,                  -- login / api_call / data_access
    resource      TEXT,                              -- 被操作的资源
    resource_id   TEXT,                              -- 被操作的具体记录 ID
    ip_address    TEXT,
    user_agent    TEXT,
    result        TEXT    NOT NULL,                  -- success / denied / error
    detail        TEXT,                              -- 详细信息 (JSON)
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_org_dept ON users(org_id, dept_id);
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_data_rules_role ON data_permission_rules(role_id, resource);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at);
```

### 3.2 Nexus 业务表权限字段扩展

**原则：只加字段，不改逻辑。不开权限系统时，这些字段为 NULL，查询不受影响。**

```sql
-- 迁移脚本：050_rbac_compat.sql

-- 所有核心业务表增加以下 4 个字段
ALTER TABLE goals      ADD COLUMN created_by TEXT;       -- 创建者 user_id
ALTER TABLE goals      ADD COLUMN org_id TEXT;           -- 所属组织
ALTER TABLE goals      ADD COLUMN dept_id TEXT;          -- 所属部门
ALTER TABLE goals      ADD COLUMN visibility TEXT DEFAULT 'org'; -- org / dept / private

ALTER TABLE projects   ADD COLUMN created_by TEXT;
ALTER TABLE projects   ADD COLUMN org_id TEXT;
ALTER TABLE projects   ADD COLUMN dept_id TEXT;
ALTER TABLE projects   ADD COLUMN visibility TEXT DEFAULT 'org';

ALTER TABLE tasks      ADD COLUMN created_by TEXT;
ALTER TABLE tasks      ADD COLUMN org_id TEXT;
ALTER TABLE tasks      ADD COLUMN dept_id TEXT;
ALTER TABLE tasks      ADD COLUMN visibility TEXT DEFAULT 'org';

ALTER TABLE scenarios  ADD COLUMN created_by TEXT;
ALTER TABLE scenarios  ADD COLUMN org_id TEXT;
ALTER TABLE scenarios  ADD COLUMN dept_id TEXT;
ALTER TABLE scenarios  ADD COLUMN visibility TEXT DEFAULT 'org';

ALTER TABLE workflows  ADD COLUMN created_by TEXT;
ALTER TABLE workflows  ADD COLUMN org_id TEXT;
ALTER TABLE workflows  ADD COLUMN dept_id TEXT;
```

**`visibility` 字段说明**：

| 值 | 含义 |
|----|------|
| `org` | 同组织可见（默认） |
| `dept` | 仅本部门可见 |
| `private` | 仅创建者可见 |
| `public` | 所有用户可见 |

---

## 四、权限模型

### 4.1 RBAC 三层模型

```
User ──N:M──> Role ──N:M──> Permission
                │
                └──> DataPermissionRule
```

```
用户 "张三"
  ├── 角色: "项目经理"
  │     ├── API 权限: goal:create, goal:read, goal:update, project:*, task:*
  │     └── 数据权限: goal → dept_and_children, project → dept_and_children
  │
  └── 角色: "普通用户"
        ├── API 权限: goal:read, task:read
        └── 数据权限: goal → self, task → self
```

### 4.2 预置角色

| 角色 | 权限范围 | 数据范围 |
|------|----------|----------|
| `super_admin` | 所有 API | 全部数据 |
| `admin` | 管理 API（不含系统设置） | 本组织全部 |
| `manager` | 读写 Goal/Project/Task | 本部门及子部门 |
| `operator` | 读写 Task | 自己创建的 + 分配给自己的 |
| `viewer` | 只读所有 | 本部门 |
| `agent` | Worker 领任务/上报 | 仅任务级 |

### 4.3 权限编码规范

```
{resource}:{action}

resource: goal | project | task | scenario | workflow | agent | system
action:   create | read | update | delete | execute | admin | *
```

---

## 五、Nexus 集成方案（可插拔）

### 5.1 配置开关

```python
# config.py
class Settings:
    # ... 现有配置 ...
    
    # === 权限系统配置 ===
    auth_enabled: bool = False                    # 总开关
    auth_service_url: str = "http://localhost:8092"  # Auth Service 地址
    auth_timeout: float = 2.0                     # 超时（秒）
    auth_cache_ttl: int = 300                     # 权限缓存 TTL（秒）
    jwt_secret: str = "change-me"                 # JWT 密钥
    jwt_expire_hours: int = 24                    # Token 过期时间
```

**`auth_enabled=false` 时**：
- Middleware 直接 pass
- Decorator 不做任何检查
- 业务代码零性能损耗

### 5.2 Middleware（请求拦截）

```python
# permission_plugin/middleware.py
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class PermissionMiddleware(BaseHTTPMiddleware):
    """
    权限中间件
    
    当 auth_enabled=true 时：
      1. 从 Header 提取 JWT Token
      2. 调用 Auth Service 验证 Token + 检查权限
      3. 将用户上下文注入 request.state
      4. 无权限则返回 403
    
    当 auth_enabled=false 时：
      直接放行，不做任何处理
    """
    
    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)
        
        # 白名单路径（不需要权限检查）
        if request.url.path in WHITE_LIST:
            return await call_next(request)
        
        # 验证 Token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        # 调用 Auth Service 验证
        auth_result = await auth_client.validate_token(token)
        if not auth_result.valid:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        # 检查 API 权限
        required_perm = resolve_permission(request)  # 根据路由解析需要的权限
        if not await auth_client.check_permission(
            user_id=auth_result.user_id,
            resource=required_perm.resource,
            action=required_perm.action,
        ):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})
        
        # 注入用户上下文
        request.state.user_id = auth_result.user_id
        request.state.user_roles = auth_result.roles
        request.state.data_scope = auth_result.data_scope  # self/dept/org/all
        
        return await call_next(request)


# 白名单
WHITE_LIST = {
    "/docs", "/openapi.json", "/health",
    "/api/v1/auth/login", "/api/v1/auth/register",
}
```

### 5.3 Decorator（细粒度控制）

```python
# permission_plugin/decorator.py
from functools import wraps
from fastapi import Request, HTTPException

def require_permission(resource: str, action: str):
    """
    接口级权限装饰器
    
    用法:
        @router.post("/goals")
        @require_permission("goal", "create")
        async def create_goal(request: Request, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.auth_enabled:
                return await func(*args, **kwargs)
            
            # 从 request 获取用户上下文（由 middleware 注入）
            req = next((a for a in args if isinstance(a, Request)), None)
            if not req or not hasattr(req.state, 'user_id'):
                raise HTTPException(status_code=500, detail="Auth middleware not active")
            
            # 再次确认权限（middleware 已做过，这里是双保险）
            if not await auth_client.check_permission(
                user_id=req.state.user_id,
                resource=resource,
                action=action,
            ):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def apply_data_filter(query, model, request: Request):
    """
    数据级权限过滤器
    
    用法（在 API handler 中）:
        @router.get("/goals")
        async def list_goals(request: Request):
            q = select(Goal)
            q = apply_data_filter(q, Goal, request)  # ← 仅此一行
            goals = await db.execute(q)
            return goals
    """
    if not settings.auth_enabled:
        return query
    
    scope = getattr(request.state, 'data_scope', 'all')
    user_id = getattr(request.state, 'user_id', None)
    dept_id = getattr(request.state, 'dept_id', None)
    org_id = getattr(request.state, 'org_id', None)
    
    if scope == 'all':
        return query
    elif scope == 'org':
        return query.where(model.org_id == org_id)
    elif scope == 'dept':
        return query.where(model.dept_id == dept_id)
    elif scope == 'self':
        return query.where(model.created_by == user_id)
    else:
        return query
```

### 5.4 业务代码改动量

**理想情况：只加装饰器 + 查询时调用 apply_data_filter**

```python
# 改动前
@router.get("/goals")
async def list_goals(request: Request):
    q = select(Goal)
    goals = await db.execute(q)
    return goals

# 改动后（开启权限时）
@router.get("/goals")
@require_permission("goal", "read")          # ← 加一行装饰器
async def list_goals(request: Request):
    q = select(Goal)
    q = apply_data_filter(q, Goal, request)  # ← 加一行过滤
    goals = await db.execute(q)
    return goals
```

**每个 API 端点最多增加 2 行代码。**

---

## 六、Auth Service 独立服务设计

### 6.1 项目结构

```
packages/auth/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── database.py          # DB 连接
│   ├── models/              # ORM 模型
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── data_rule.py
│   │   └── audit.py
│   ├── services/
│   │   ├── user_service.py
│   │   ├── role_service.py
│   │   ├── permission_service.py
│   │   ├── auth_service.py     # 登录/JWT
│   │   └── data_filter.py      # 数据权限引擎
│   ├── api/
│   │   ├── auth_router.py      # 登录/注册/刷新
│   │   ├── user_router.py      # 用户 CRUD
│   │   ├── role_router.py      # 角色 CRUD
│   │   ├── permission_router.py # 权限 CRUD
│   │   └── audit_router.py     # 审计日志
│   └── middleware/
│       └── security.py         # CORS, rate limit
├── migrations/
│   └── 001_init.sql
├── tests/
├── pyproject.toml
└── Dockerfile
```

### 6.2 对外 API

```
POST   /api/v1/auth/login           # 登录 → 返回 JWT
POST   /api/v1/auth/register        # 注册
POST   /api/v1/auth/refresh         # 刷新 Token
POST   /api/v1/auth/logout          # 登出

GET    /api/v1/users                # 用户列表
POST   /api/v1/users                # 创建用户
GET    /api/v1/users/{id}           # 用户详情
PATCH  /api/v1/users/{id}           # 更新用户
DELETE /api/v1/users/{id}           # 删除用户
POST   /api/v1/users/{id}/roles     # 分配角色

GET    /api/v1/roles                # 角色列表
POST   /api/v1/roles                # 创建角色
PATCH  /api/v1/roles/{id}           # 更新角色
DELETE /api/v1/roles/{id}           # 删除角色
POST   /api/v1/roles/{id}/perms     # 分配权限

GET    /api/v1/permissions          # 权限列表（全部）
GET    /api/v1/data-rules           # 数据权限规则
POST   /api/v1/data-rules           # 创建数据规则

POST   /api/v1/validate             # Nexus 调用：验证 Token+权限
POST   /api/v1/data-filter          # Nexus 调用：获取数据过滤条件

GET    /api/v1/audit                # 审计日志
GET    /health                      # 健康检查
```

### 6.3 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Nexus Server | 8091 | 主业务 |
| Auth Service | 8092 | 权限服务 |
| Nexus Frontend | 5173 | 前端 |

### 6.4 JWT 结构

```json
{
  "sub": "usr-abc123",
  "username": "zhangsan",
  "roles": ["manager", "operator"],
  "org_id": "org-001",
  "dept_id": "dept-003",
  "data_scope": "dept_and_children",
  "iat": 1715040000,
  "exp": 1715126400,
  "jti": "uuid-xxx"
}
```

---

## 七、数据权限过滤引擎

### 7.1 过滤逻辑

```python
class DataFilterEngine:
    """
    数据权限过滤引擎
    
    输入: user_id + resource + query
    输出: 加上 WHERE 条件的 query
    """
    
    async def filter(self, user_id: str, resource: str, query) -> query:
        # 1. 查用户的所有角色
        roles = await self.get_user_roles(user_id)
        
        # 2. 合并所有角色的数据权限规则，取最大范围
        max_scope = self.merge_scopes(
            await self.get_data_rules(roles, resource)
        )
        
        # 3. 应用过滤
        return self.apply_scope(query, resource, max_scope, user_id)
    
    def merge_scopes(self, scopes: list[str]) -> str:
        """取最大数据范围: all > org > dept_and_children > dept > self"""
        priority = {'all': 5, 'org': 4, 'dept_and_children': 3, 'dept': 2, 'self': 1}
        return max(scopes, key=lambda s: priority.get(s, 0))
    
    def apply_scope(self, query, resource: str, scope: str, user_id: str) -> query:
        user = get_user(user_id)
        model = get_model(resource)
        
        if scope == 'all':
            return query
        elif scope == 'org':
            return query.where(model.org_id == user.org_id)
        elif scope == 'dept_and_children':
            dept_ids = self.get_all_child_dept_ids(user.dept_id)
            return query.where(model.dept_id.in_(dept_ids))
        elif scope == 'dept':
            return query.where(model.dept_id == user.dept_id)
        elif scope == 'self':
            return query.where(model.created_by == user_id)
        else:
            return query
```

### 7.2 visibility 字段与数据权限的关系

最终可见数据 = **数据权限规则 ∩ visibility 字段**

```
用户数据范围: dept_and_children（部门及子部门）
记录 visibility: dept（仅本部门）
→ 该用户能看到本部门 + 子部门中 visibility 为 org/all 的记录
→ 看不到 visibility=private 且 created_by≠自己的记录
```

---

## 八、前端页面设计

### 8.1 路由结构

```
/auth/login              ← 登录页
/auth/register           ← 注册页（可选，管理员可关闭）
/system/users            ← 用户管理（Tab 页：用户列表 / 组织 / 部门）
/system/roles            ← 角色管理 + 权限分配
/system/permissions      ← 权限字典（只读/管理 API 权限）
/system/audit            ← 审计日志
```

### 8.2 页面 1：登录页 `/auth/login`

**布局**：居中卡片，Nexus 品牌色

```
┌──────────────────────────────────────────────┐
│                                              │
│           🛡️  Nexus RBAC                     │
│         权限认证系统                          │
│                                              │
│  ┌────────────────────────────────────┐      │
│  │  用户名                             │      │
│  │  [________________]                │      │
│  │                                    │      │
│  │  密码                               │      │
│  │  [________________] 👁              │      │
│  │                                    │      │
│  │  □ 记住我                           │      │
│  │                                    │      │
│  │  [───── 登 录 ─────]               │      │
│  │                                    │      │
│  │  还没有账号？ 联系管理员创建         │      │
│  └────────────────────────────────────┘      │
│                                              │
└──────────────────────────────────────────────┘
```

**交互**：
- 输入用户名 + 密码 → POST `/api/v1/auth/login` → 返回 JWT
- JWT 存入 `localStorage` + `AuthContext`
- 登录失败显示 toast 错误（密码错误/账号锁定）
- 失败 5 次 → 账号锁定 15 分钟，toast 提示
- "记住我" → 同时存 refresh token（7 天过期）
- 登录成功 → 重定向到原页面或 `/`

**组件**：`/src/pages/AuthLogin.tsx`

### 8.3 页面 2：用户管理 `/system/users`

**布局**：Tab 页结构（用户列表 | 组织 | 部门）

```
┌──────────────────────────────────────────────────────────────────┐
│  系统管理 › 用户管理                                              │
│                                                                  │
│  [用户列表]  [组织]  [部门]                                       │
│  ───────────                                                     │
│                                                                  │
│  [+ 新建用户]                    [🔍 搜索用户...]                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 用户名   │ 显示名 │ 组织   │ 部门   │ 角色        │ 状态  │ │
│  ├──────────┼────────┼────────┼────────┼─────────────┼───────┤ │
│  │ zhangsan │ 张三   │ 总公司 │ 技术部 │ admin       │ ✅    │ │
│  │          │        │        │        │ manager     │       │ │
│  ├──────────┼────────┼────────┼────────┼─────────────┼───────┤ │
│  │ lisi     │ 李四   │ 总公司 │ 运营部 │ operator    │ ✅    │ │
│  ├──────────┼────────┼────────┼────────┼─────────────┼───────┤ │
│  │ wangwu   │ 王五   │ 分公司 │ 技术部 │ viewer      │ 🔒    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  第 1-10 条，共 23 条   < 1  2  3 ...  >                        │
└──────────────────────────────────────────────────────────────────┘
```

**操作**：
- **新建用户** → 弹出 Modal：用户名、密码、显示名、邮箱、手机、组织、部门、角色（多选）、状态
- **编辑** → 行尾编辑按钮，弹出同上 Modal（回填数据）
- **删除** → 确认弹窗 → 软删除（status → deleted）
- **分配角色** → 行尾角色下拉，点击弹出角色分配面板（可多选，显示已分配角色标签）
- **重置密码** → 管理员可为用户重置密码
- **锁定/解锁** → 切换 status

**新建用户 Modal**：

```
┌──────────────────────────────────┐
│  新建用户                    [×]  │
├──────────────────────────────────┤
│  用户名 *    [____________]       │
│  密码 *      [____________] 👁     │
│  确认密码 *  [____________]       │
│  显示名      [____________]       │
│  邮箱        [____________]       │
│  手机        [____________]       │
│  组织        [总公司 ▼]           │
│  部门        [技术部 ▼]           │
│  角色 *      [admin ✓] [manager]  │
│             [operator] [viewer]   │
│             [agent]               │
│  状态        [● 启用 ○ 禁用]      │
│                                  │
│  [取消]  [创建]                   │
└──────────────────────────────────┘
```

**Tab 2：组织管理**：

```
[+ 新建组织]

┌─────────────────────────────────┐
│ 组织名称 │ 上级组织 │ 状态 │ 操作│
├──────────┼──────────┼──────┼───┤
│ 总公司   │ —        │ ✅   │ 编辑│
│ 分公司A  │ 总公司   │ ✅   │ 编辑│
│ 分公司B  │ 总公司   │ ✅   │ 编辑│
│ 深圳分部 │ 分公司A  │ ✅   │ 编辑│
└─────────────────────────────────┘
```

**Tab 3：部门管理**：

```
[+ 新建部门]  组织筛选: [全部 ▼]

┌──────────────────────────────────────┐
│ 部门名称 │ 所属组织 │ 上级部门 │ 操作 │
├──────────┼──────────┼──────────┼─────┤
│ 技术部   │ 总公司   │ —        │ 编辑 │
│ 运营部   │ 总公司   │ —        │ 编辑 │
│ 前端组   │ 总公司   │ 技术部   │ 编辑 │
│ 后端组   │ 总公司   │ 技术部   │ 编辑 │
└──────────────────────────────────────┘
```

**文件**：`/src/pages/system/UserManagement.tsx`

### 8.4 页面 3：角色管理 `/system/roles`

**布局**：左侧角色列表 + 右侧权限配置面板（左右分栏）

```
┌──────────────────────────────────────────────────────────────────┐
│  系统管理 › 角色管理                                               │
│                                                                  │
│  [+ 新建角色]                                                     │
│                                                                  │
│  ┌───────────────────┐  ┌────────────────────────────────────┐  │
│  │  角色列表          │  │  角色详情: 项目经理                 │  │
│  │                  │  │                                    │  │
│  │  ● super_admin   │  │  基本信息                           │  │
│  │  ● admin         │  │  名称: 项目经理                     │  │
│  │  ● manager ◀     │  │  编码: manager                      │  │
│  │  ● operator      │  │  描述: 项目管理人员                  │  │
│  │  ● viewer        │  │  类型: 系统内置                     │  │
│  │  ● agent         │  │                                    │  │
│  │                  │  │  API 权限                           │  │
│  │                  │  │  ☑ goal:create   ☑ goal:read       │  │
│  │                  │  │  ☑ goal:update   ☐ goal:delete     │  │
│  │                  │  │  ☑ project:*     ☑ task:*          │  │
│  │                  │  │  ☐ scenario:*    ☐ workflow:*      │  │
│  │                  │  │  ☐ agent:*       ☐ system:*        │  │
│  │                  │  │                                    │  │
│  │                  │  │  数据权限                           │  │
│  │                  │  │  goal:        [本部门及子部门 ▼]    │  │
│  │                  │  │  project:     [本部门及子部门 ▼]    │  │
│  │                  │  │  task:        [自己创建的 ▼]        │  │
│  │                  │  │  scenario:    [本部门 ▼]           │  │
│  │                  │  │  workflow:    [本部门及子部门 ▼]    │  │
│  │                  │  │                                    │  │
│  │                  │  │  已分配用户 (3)                     │  │
│  │                  │  │  👤 张三  👤 李四  👤 王五          │  │
│  │                  │  │                                    │  │
│  │                  │  │  [保存更改]  [删除角色]             │  │
│  └───────────────────┘  └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**交互**：
- 点击左侧角色 → 右侧加载详情
- API 权限：按资源分组显示，checkbox 勾选
  - 支持 `*` 通配（选中 `goal:*` = 自动选中 goal 下所有 action）
- 数据权限：下拉框选规则（self / dept / dept_and_children / org / all）
- 已分配用户：显示用户标签，点击 × 可移除
- 新建角色 → 右侧表单清空，填写后保存
- 系统内置角色（role_type=system）不可删除，只可改权限

**新建角色 Modal**（从左侧 [+ 新建角色] 触发）：

```
┌──────────────────────────────────┐
│  新建角色                    [×]  │
├──────────────────────────────────┤
│  角色名称 *   [____________]      │
│  显示名称 *   [____________]      │
│  描述         [____________]      │
│  所属组织     [全局 ▼]            │
│                                  │
│  [下一步: 配置权限 →]             │
└──────────────────────────────────┘
```

**文件**：`/src/pages/system/RoleManagement.tsx`

### 8.5 页面 4：权限字典 `/system/permissions`

**布局**：权限矩阵表格（只读为主，管理员可新增）

```
┌──────────────────────────────────────────────────────────────────┐
│  系统管理 › 权限字典                                               │
│                                                                  │
│  [刷新]  [🔍 搜索权限...]                                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 资源      │ 操作       │ 类型 │ 描述              │ 状态   │ │
│  ├───────────┼───────────┼──────┼───────────────────┼────────┤ │
│  │ goal      │ create    │ API  │ 创建目标          │ 内置   │ │
│  │ goal      │ read      │ API  │ 查看目标          │ 内置   │ │
│  │ goal      │ update    │ API  │ 编辑目标          │ 内置   │ │
│  │ goal      │ delete    │ API  │ 删除目标          │ 内置   │ │
│  │ project   │ *         │ API  │ 项目所有操作      │ 内置   │ │
│  │ task      │ create    │ API  │ 创建任务          │ 内置   │ │
│  │ task      │ read      │ API  │ 查看任务          │ 内置   │ │
│  │ task      │ execute   │ API  │ 执行任务          │ 内置   │ │
│  │ scenario  │ read      │ data │ 场景数据访问      │ 内置   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [+ 新增自定义权限]                                               │
└──────────────────────────────────────────────────────────────────┘
```

**说明**：大部分权限是系统预置的，此页面主要用于查看和少量自定义权限添加。

**文件**：`/src/pages/system/PermissionList.tsx`

### 8.6 页面 5：审计日志 `/system/audit`

**布局**：日志表格 + 筛选栏（沿用 SecurityCenter 风格）

```
┌──────────────────────────────────────────────────────────────────┐
│  系统管理 › 审计日志                                               │
│                                                                  │
│  [🔍 搜索...]  用户: [全部 ▼]  操作: [全部 ▼]  结果: [全部 ▼]    │
│  时间: [2026-05-01] ~ [2026-05-07]  [查询]  [导出 CSV]          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 时间              │ 用户  │ 操作       │ 资源    │ 结果  │  │
│  ├───────────────────┼───────┼───────────┼─────────┼───────┤  │
│  │ 2026-05-07 10:20  │ 张三  │ 登录      │ —       │ ✅    │  │
│  │ 2026-05-07 10:21  │ 张三  │ api_call  │ goal    │ ✅    │  │
│  │ 2026-05-07 10:22  │ 李四  │ api_call  │ goal    │ ❌    │  │
│  │                   │       │           │         │ 403   │  │
│  │ 2026-05-07 09:15  │ admin │ 分配角色  │ 王五    │ ✅    │  │
│  │                   │       │           │         │       │  │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  第 1-10 条，共 1,234 条   < 1  2  3 ... 124 >                   │
└──────────────────────────────────────────────────────────────────┘
```

**操作**：
- 筛选：用户 / 操作类型 / 结果状态 / 时间范围
- 导出 CSV
- 点击行 → 弹出详情 Modal 显示完整信息（IP、User-Agent、请求详情 JSON）

**文件**：`/src/pages/system/AuditLogs.tsx`

### 8.7 全局组件

#### 8.7.1 AuthContext + 路由守卫

```typescript
// /src/context/AuthContext.tsx
interface AuthContext {
  user: User | null;
  roles: string[];
  permissions: string[];        // ['goal:create', 'goal:read', ...]
  dataScope: string;            // 'self' | 'dept' | 'org' | 'all'
  hasPermission: (perm: string) => boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

// 路由保护
<Route path="/goals" element={
  <ProtectedRoute requiredPerm="goal:read">
    <GoalList />
  </ProtectedRoute>
} />
```

#### 8.7.2 权限按钮组件

```tsx
// 无权限时不渲染
<PermButton perm="goal:create">
  <Button onClick={handleCreate}>新建目标</Button>
</PermButton>

// 无权限时禁用
<PermButton perm="goal:delete" mode="disable">
  <Button onClick={handleDelete}>删除</Button>
</PermButton>
```

#### 8.7.3 顶栏用户信息

```
┌─────────────────────────────────────────────────┐
│ Nexus    工作台  协同中心  ...  系统管理    ▼    │
│                                   ┌───────────┐ │
│                              👤 张三│ admin     │ │
│                                   │ 个人设置  │ │
│                                   │ 切换角色  │ │
│                                   │ 登出      │ │
│                                   └───────────┘ │
└─────────────────────────────────────────────────┘
```

### 8.8 页面文件清单

```
packages/ui/src/
├── context/
│   └── AuthContext.tsx          ← 新增：全局 Auth 状态
├── components/
│   └── PermButton.tsx           ← 新增：权限控制按钮
├── pages/
│   ├── AuthLogin.tsx            ← 新增：登录页
│   └── system/
│       ├── UserManagement.tsx   ← 新增：用户管理（含组织/部门 Tab）
│       ├── RoleManagement.tsx   ← 新增：角色管理 + 权限配置
│       ├── PermissionList.tsx   ← 新增：权限字典
│       └── AuditLogs.tsx        ← 新增：审计日志
├── utils/
│   └── authApi.ts               ← 新增：Auth Service API 封装
└── layout/
    └── MainLayout.tsx           ← 修改：顶栏加用户信息下拉
```

---

## 九、技术选型：UI 组件库

### 9.1 现状

```
当前依赖:
✅ Tailwind CSS       — 原子化样式
✅ lucide-react       — 图标
✅ @xyflow/react      — DAG 流程图
❌ 无任何 UI 组件库
```

所有表格、弹窗、分页、按钮、表单均为手写。37 个页面 + 9 个组件。

### 9.2 选择：shadcn/ui

| 特性 | 说明 |
|------|------|
| **本质** | 不是 npm 包，是复制源码到项目（`src/components/ui/`） |
| **底层** | Radix UI（无障碍访问已做好）+ Tailwind CSS |
| **风格** | 完全可定制，和现有 Tailwind 风格无缝衔接 |
| **体积** | 按需安装，不增加 `node_modules` 垃圾 |
| **社区** | GitHub 114k+ stars，React 生态最火 UI 方案 |

### 9.3 AI 加速：Skill + MCP

**Skill**（`npx skills add shadcn/ui`）：
- 自动注入项目上下文（框架、别名、已装组件、Tailwind 版本）
- 子代理写迁移代码时不再猜 import 路径，API 一次对

**MCP Server**（`.mcp.json` 配置）：
- AI 通过自然语言浏览/搜索/安装组件
- 5 个 MCP 工具：browse、search、docs、view、add
- 详见 [Sprint 63 迁移计划](./sprint63-ui-migration-plan.md#九mcp--skill-集成加速迁移工作流)

### 9.4 需要安装的组件

```bash
npx shadcn@latest add button          # 按钮
npx shadcn@latest add input           # 输入框
npx shadcn@latest add dialog          # 弹窗/Modal
npx shadcn@latest add table           # 表格
npx shadcn@latest add tabs            # Tab 切换
npx shadcn@latest add select          # 下拉框
npx shadcn@latest add checkbox        # 复选框
npx shadcn@latest add badge           # 状态标签
npx shadcn@latest add dropdown-menu   # 下拉菜单
npx shadcn@latest add toast           # 通知提示
npx shadcn@latest add form            # 表单（+ react-hook-form + zod）
npx shadcn@latest add avatar          # 头像
npx shadcn@latest add card            # 卡片容器
npx shadcn@latest add separator       # 分割线
npx shadcn@latest add pagination      # 分页
npx shadcn@latest add tooltip         # 工具提示
```

### 9.5 预期效果

| 指标 | 手写 | shadcn/ui | 缩减 |
|------|------|-----------|------|
| 单个列表页面 | ~150 行 | ~60 行 | -60% |
| 单个弹窗/表单 | ~100 行 | ~40 行 | -60% |
| RBAC 5 个页面 | ~2000 行 | ~800 行 | -60% |
| 全 37 页面迁移 | — | ~1500 行 → ~600 行 | -60% |

---

## 十、实施阶段

### Phase 0: UI 组件库引入 + 全量迁移（Sprint 63，~3 天）

> 在 RBAC 开发之前先完成，所有页面统一风格后再做新功能。

**Step 1: 安装 shadcn/ui（半天）**
- [ ] `npx shadcn@latest init` 初始化
- [ ] 安装 16 个核心组件（见 9.3）
- [ ] 安装 `react-hook-form` + `zod`（表单验证）
- [ ] 验证构建通过，旧页面不受影响

**Step 2: 替换通用组件（半天）**
- [ ] 手写 `Pagination.tsx` → `shadcn Pagination`
- [ ] 手写 Modal → `shadcn Dialog`
- [ ] 手写按钮 → `shadcn Button`
- [ ] 手写输入框 → `shadcn Input`
- [ ] 手写 Badge → `shadcn Badge`
- [ ] 手写 Toast 通知 → `shadcn Toast`

**Step 3: 页面逐批迁移（2 天，每批 5-6 个页面）**

| 批次 | 页面 | 复杂度 |
|------|------|--------|
| 第一批 | Dashboard, GoalList, ProjectList, TaskList, AgentList | ⭐⭐ 简单表格+卡片 |
| 第二批 | GoalDetail, ProjectDetail, TaskDetail, EnhancedTaskDetail, ScenarioList | ⭐⭐⭐ 详情+表单 |
| 第三批 | CreateGoal, ScenarioCreate, ScenarioDetail, ScenarioCenter, ScenarioFavorites | ⭐⭐⭐ 表单为主 |
| 第四批 | SecurityCenter, HumanInputDashboard, HumanInputAnalytics, CognitiveCenter, CognitiveKnowledge | ⭐⭐ 表格+图表 |
| 第五批 | ExecutionDetail, ExecutionMonitoring, VisualBoard, WorkflowDiagram, RulingsPage | ⭐⭐⭐⭐ 复杂交互 |
| 第六批 | 其余页面（ArtifactList, CapabilitiesPage, CognitiveAssessment 等） | ⭐⭐ 简单页面 |
| 第七批 | AgentDetailModal, AgentRegisterModal, ExecutionReportModal, Sidebar | ⭐⭐ 弹窗+导航 |

**Step 4: 回归验证（半天）**
- [ ] 所有页面可正常渲染
- [ ] 关键交互正常（创建/编辑/删除/筛选）
- [ ] 响应式布局正常
- [ ] TypeScript 编译 0 errors

### Phase 1: Auth Service 基础（~3 天）
- [ ] 数据库表创建（migrations/001_init.sql）
- [ ] 用户管理 CRUD API
- [ ] 角色管理 CRUD API
- [ ] 权限管理 CRUD API
- [ ] 登录/JWT 签发/验证
- [ ] 健康检查端点

### Phase 2: 数据权限引擎（~2 天）
- [ ] 数据权限规则 CRUD
- [ ] DataFilterEngine 实现
- [ ] /validate 端点（供 Nexus 调用）
- [ ] /data-filter 端点（供 Nexus 获取过滤条件）

### Phase 3: Nexus 集成（~2 天）
- [ ] permission_plugin 包创建（middleware + decorator）
- [ ] config.py 增加 auth_enabled 开关
- [ ] 业务表迁移脚本（050_rbac_compat.sql）
- [ ] 白名单配置
- [ ] 端到端测试（开/关两种模式）

### Phase 4: RBAC 前端页面（~2 天）
- [ ] AuthLogin 登录页
- [ ] UserManagement 用户管理
- [ ] RoleManagement 角色管理
- [ ] PermissionList 权限字典
- [ ] AuditLogs 审计日志
- [ ] AuthContext + 路由守卫
- [ ] PermButton 权限按钮组件
- [ ] MainLayout 顶栏用户信息

### Phase 5: 业务 API 接入（按需，每批 ~1 天）
- [ ] Goals API 接入
- [ ] Projects API 接入
- [ ] Tasks API 接入
- [ ] Scenarios API 接入
- [ ] Workflows API 接入

---

## 十一、关键技术决策

### 10.1 为什么用独立服务而非库？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **独立服务**（推荐） | 完全解耦、独立部署、可被其他系统复用 | 多一个进程 |
| 嵌入式库 | 部署简单 | 耦合 Nexus、升级影响主系统 |

### 10.2 为什么用 SQLite 而非 PostgreSQL？

Nexus 当前用 SQLite，Auth Service 保持一致。如果后续有多租户/高并发需求，可迁移到 PostgreSQL，接口不变。

### 10.3 权限缓存策略

```
Nexus 本地缓存用户权限（TTL 300s）
  ↓ cache miss
调用 Auth Service /validate
  ↓
Auth Service 返回: {valid, user_id, roles, data_scope, perms[]}
  ↓
Nexus 缓存 300s
```

### 10.4 降级策略

```
Auth Service 不可达？
  → 使用本地缓存（如果未过期）
  → 缓存也过期？
    → auth_enabled=true: 拒绝请求（安全优先）
    → auth_enabled=false: 放行（本来就是关的）
```

---

## 十二、安全考虑

| 项目 | 方案 |
|------|------|
| 密码存储 | bcrypt (cost=12) |
| Token 类型 | JWT (RS256 或 HS256) |
| Token 过期 | 24 小时 access + 7 天 refresh |
| 暴力破解 | 登录失败 5 次锁定 15 分钟 |
| XSS 防护 | HTTP-only cookie 存 refresh token |
| CSRF | SameSite cookie + CSRF token |
| 审计 | 所有权限操作写 audit_logs |
| 注入防护 | SQLAlchemy ORM 参数化查询 |

---

## 十三、总结

**核心优势**：

1. **零侵入起步** — `auth_enabled=false`，业务代码完全不动
2. **渐进式接入** — 开启后只需加装饰器 + 一行过滤
3. **独立部署** — Auth Service 可独立升级、独立扩展
4. **可复用** — 其他系统（如谷子的交易系统）也能用同一套权限服务
5. **DB 兼容** — 业务表预留字段，不开权限不产生额外查询开销

**每个 API 接入成本：2 行代码（装饰器 + 数据过滤）**。

**总体时间线**：

| 阶段 | 内容 | 预估时间 |
|------|------|----------|
| Sprint 63 | UI 组件库 + 全量迁移 | ~3 天 |
| Phase 1 | Auth Service 基础 | ~3 天 |
| Phase 2 | 数据权限引擎 | ~2 天 |
| Phase 3 | Nexus 集成 | ~2 天 |
| Phase 4 | RBAC 前端 | ~2 天 |
| Phase 5 | 业务 API 接入 | ~5 天（分批） |
| **合计** | | **~17 天** |
