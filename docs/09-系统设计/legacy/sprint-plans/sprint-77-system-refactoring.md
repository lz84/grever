# Sprint 77: 系统重构 — 技术债务清零

> 创建日期：2026-05-13
> 创建人：刚子
> 状态：**执行中**
> 今日完成：30 个 commit + 验证脚本
> 后端端口：8095（8090 被占用）

## 执行记录（2026-05-13）

| 任务 | 状态 | 提交 | 说明 |
|------|------|------|------|
| P0-4 验证 bypass | ✅ 完成 | `ade05c3` | 删 _legacy_verify，无 criteria → review_needed |
| P0-7 SQL注入 | ✅ 完成 | `e2c2c87` | LIMIT/OFFSET int 强制转换 |
| P0-8 DB备份 | ✅ 完成 | `e2c2c87` | scripts/backup_db.py |
| P1-5 print→logging | ✅ 完成 | `8340dc3` | 230+ 处，19 文件 |
| P1-6 复合索引 | ✅ 完成 | `810743d` | 5 个新索引 |
| P1-4 错误响应 | ✅ 完成 | `345f752` | error_codes.py + error_handler.py |
| P1-9 分页API | ✅ 完成 | `f65729f` | list_tasks 返回 total |
| P2-1 魔法数字 | ✅ 完成 | `4ed7cf6` | reins/config.py + 调度器/验证器更新 |
| P2-3 日志清理 | ✅ 完成 | `98f559c` | scripts/cleanup_logs.py |
| P2-4 敏感数据脱敏 | ✅ 完成 | `dec3e34` | reins/sanitize.py |
| P2-5 审计日志 | ✅ 完成 | `57744ce` | reins/audit.py |
| P2-6 场景匹配记录 | ✅ 完成 | `dec3e34` | agent_matcher.py 添加日志 |
| P0-3 Agent 去双写 | ✅ 完成 | `89205c8` | 删除 server.py 启动加载 + ReinsServer 双写，-99行 |
| P1-1 Goal.project_id | ✅ 完成 | `ee311f3` | 从模型删除，goals.py 用 Project.goal_id 替代 |
| P1-10 工作流异步 | ✅ 完成 | `ee311f3` | execute_workflow 改 BackgroundTasks |

## P0 完成状态

| P0 任务 | 状态 | 提交 | 说明 |
|---------|------|------|------|
| P0-1 server.py 拆分 | ⏳ 暂缓 | — | 需要更多测试，当前不影响功能 |
| P0-2 Alembic 迁移 | ⏳ 暂缓 | — | 当前 ReinsMigrator 可用，后续迁移时切换 |
| P0-3 Agent 去双写 | ✅ | `89205c8` | 删除双写，-99行 |
| P0-4 验证 bypass | ✅ | `ade05c3` | 无 criteria → review_needed |
| P0-5 任务状态统一 | ✅ 已部分 | — | DEV-GUIDE 已更新 |
| P0-6 测试覆盖 | ⏳ 后续 | — | 核心逻辑重构后再加 |
| P0-7 SQL 注入 | ✅ | `f95adfb` | LIMIT/OFFSET 修复 |
| P0-8 DB 备份 | ✅ | `f95adfb` | scripts/backup_db.py |
> 决策依据：005-complete-problem-analysis.md 中确认的 7 项决策

---

## Sprint 最终进度（2026-05-13）

**已完成：16 个 commit**

### P0 完成：5/8
| 任务 | 状态 | 提交 |
|------|------|------|
| P0-3 Agent 去双写 | ✅ | `89205c8` |
| P0-4 验证 bypass | ✅ | `ade05c3` |
| P0-7 SQL 注入 | ✅ | `f95adfb` |
| P0-8 DB 备份 | ✅ | `f95adfb` |
| P0-1/2/5/6 | ⏳ 暂缓 | — |

### P1 完成：6/10
| 任务 | 状态 | 提交 |
|------|------|------|
| P1-3 N+1 查询 | ✅ | 代码分析确认无显著问题 |
| P1-4 错误响应 | ✅ | `345f752` |
| P1-5 print→logging | ✅ | `8340dc3` |
| P1-6 复合索引 | ✅ | `810743d` |
| P1-9 分页 API | ✅ | `c1e1813` |
| P1-1 Goal.project_id | ✅ | `ee311f3` |
| P1-10 工作流异步 | ✅ | `ee311f3` |

### P2 完成：5/6
| 任务 | 状态 | 提交 |
|------|------|------|
| P2-1 魔法数字 | ✅ | `4ed7cf6` |
| P2-3 日志清理 | ✅ | `98f559c` |
| P2-4 敏感数据 | ✅ | `dec3e34` |
| P2-5 审计日志 | ✅ | `57744ce` |
| P2-6 场景匹配 | ✅ | `dec3e34` |

### 其他成果
- M6: 清理 traces 路由重复定义（删除 21 行死代码）
- Alembic 迁移脚本已创建待执行
- 敏感数据脱敏工具 reins/sanitize.py
- 全局错误码枚举 reins/api/error_codes.py
- 日志表清理脚本 scripts/cleanup_logs.py

### 未完成（高风险，需测试保障）
- P1-2 Task 模型瘦身（40+ 字段，DB 迁移风险高）
- P1-1 Task.goal_id 删除（DB schema 变更，需充分测试）
- P0-1 server.py 拆分（需端到端测试）
- P0-2 Alembic 迁移切换（需回滚方案）
- P0-6 测试覆盖（需在以上重构完成后）

---

## Sprint 概览

**时间**：4 周（20 个工作日）
**原则**：冻结新功能开发，专注技术债务清理
**目标**：消除 10 组元问题中的 7 组，修复 8 个 P0 问题

### 成功标准

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| server.py 行数 | 3148 | ≤ 50 |
| 迁移系统数 | 3 套 | 1 套（Alembic） |
| Agent 双写 | 有 | 无（纯 DB） |
| TaskStatus 体系 | 3 套 | 1 套（枚举 10 种） |
| 验证 bypass | 有 | 无 |
| 单元测试覆盖 | 0 模块 | 4 核心模块 |
| 路由重复定义 | 有 | 0 |

---

## Phase 0：止血（2 天）

**目标**：修复最危险、最容易修的问题

### Task 0-1: 修复验证 bypass（P0-4）

**文件**：
- `packages/server/src/reins/scheduler/result_verifier.py`
- `packages/server/src/reins/api/tasks.py`

**改动**：
1. 删除 `_legacy_verify()` 方法
2. `trigger_verification()` 无 criteria 时返回 `review_needed`（不再自动 done）
3. `create_task` 端点：无 `acceptance_criteria` 时拒绝创建
4. `goal_decomposition` 服务：批量创建时生成默认验收标准

**Done Criteria**：
- [ ] `verify()` 不再有 `_legacy_verify` 分支
- [ ] 无 criteria 的任务无法通过验证（单元测试）
- [ ] create_task 无 criteria 时返回 400
- [ ] 现有有 criteria 的任务正常验证

**预计**：0.5 天

---

### Task 0-2: 修复 SQL 注入风险（P0-7）

**文件**：
- `packages/server/src/reins/api/server.py`

**改动**：
1. `security_list_alerts` 端点：修复 `f"WHERE {where}"` 拼接
2. 所有动态 WHERE 条件改为参数化查询

**Done Criteria**：
- [ ] 无 f-string SQL 拼接
- [ ] 所有查询用参数化
- [ ] 现有 API 功能正常（curl 测试）

**预计**：0.5 天

---

### Task 0-3: 添加 DB 备份脚本（P0-8）

**文件**：
- `packages/server/scripts/backup_db.py`（新建）
- Windows 任务计划 / cron

**改动**：
1. 创建备份脚本：复制 `data/reins.db` 到备份目录
2. 命名格式：`reins_YYYYMMDD_HHMMSS.db`
3. 保留最近 30 天的备份
4. 添加 Windows 任务计划（每日 2:00 AM）

**Done Criteria**：
- [ ] 脚本能正常执行
- [ ] 备份目录有备份文件
- [ ] 超过 30 天的备份被清理
- [ ] Windows 任务计划已创建

**预计**：0.5 天

---

### Task 0-4: print → logging 全局替换（P1-5）

**文件**：
- 全局搜索 `print(` 在 Python 源码中

**改动**：
1. `server.py` 中 81 处 print → `logger.info/debug/error`
2. 其他 Python 文件中所有 print → logger
3. 错误日志加 `exc_info=True`

**Done Criteria**：
- [ ] 全局无 `print(` 在业务代码中（允许 seed 脚本保留）
- [ ] logger 格式统一：`[模块名] 消息`
- [ ] 错误日志包含堆栈

**预计**：0.5 天

---

## Phase 1：基础设施重构（8 天）

**目标**：统一迁移系统 + 扩展任务状态枚举 + 统一错误处理

### Task 1-1: 统一 Alembic 迁移（P0-2, M1）

**文件**：
- `alembic.ini`（新建）
- `alembic/versions/`（新建）
- `packages/server/src/reins/persistence/migrations/`（删除）
- `packages/server/src/reins/migration/`（删除）
- `packages/server/src/reins/api/server.py`（清理内联迁移）

**改动**：
1. `pip install alembic`
2. `alembic init alembic`
3. 导出当前 DB schema：`sqlite3 data/reins.db ".schema"`
4. 生成基准迁移：`alembic revision --autogenerate -m "baseline"`
5. 删除 `persistence/migrations/` 所有文件
6. 删除 `reins/migration/` 所有文件
7. 删除 server.py `_lifespan()` 中的所有迁移代码
8. 保留 `_lifespan()` 中的后台任务初始化 + 数据加载
9. 后续所有 migration 通过 `alembic revision`

**Done Criteria**：
- [ ] `alembic upgrade head` 能成功执行
- [ ] DB schema 不变
- [ ] `persistence/migrations/` 目录不存在
- [ ] `reins/migration/` 目录不存在
- [ ] server.py `_lifespan()` 中无 `ALTER TABLE` / `CREATE TABLE`
- [ ] `alembic downgrade -1` 能回滚

**预计**：3 天

---

### Task 1-2: 扩展 TaskStatus 到 10 种（P0-5, M2）

**文件**：
- `packages/server/src/reins/models/task.py`
- `packages/server/src/reins/state_machine.py`（删除）
- `packages/server/src/reins/api/tasks.py`
- `packages/ui/src/utils/statusMap.ts`

**改动**：
1. 扩展 TaskStatus 枚举到 10 种
2. 删除 `TaskState` 和 `TaskStateMachine`（与 TaskStatus 重复）
3. 更新所有状态转换逻辑，使用 TaskStatus
4. 更新 `statusMap.ts` 与后端完全对齐
5. 添加 DB CHECK 约束（Alembic 迁移）

**最终枚举**：
```python
class TaskStatus(str):
    BACKLOG = 'backlog'
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    REVIEW_NEEDED = 'review_needed'   # 真实业务，阻断
    VERIFYING = 'verifying'           # 真实业务，阻断
    DISPUTED = 'disputed'             # 真实业务，阻断
    WAITING_HUMAN = 'waiting_human'   # 真实业务，阻断
    BLOCKED = 'blocked'
    DONE = 'done'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    PAUSED = 'paused'
    CANCELLED = 'cancelled'
```

**Done Criteria**：
- [ ] TaskStatus 枚举包含全部 13 种状态
- [ ] TaskState/TaskStateMachine 已删除
- [ ] 所有隐式状态赋值改为 TaskStatus 枚举
- [ ] DB CHECK 约束已添加
- [ ] `statusMap.ts` 与后端完全对齐
- [ ] 前端状态展示正常（手动测试）

**预计**：1 天

---

### Task 1-3: 统一错误响应格式（P1-4, M10）

**文件**：
- `packages/server/src/reins/api/error_codes.py`（新建）
- `packages/server/src/reins/api/error_handler.py`（新建）
- 全局所有 router 文件

**改动**：
1. 定义 `NexusErrorCode` 枚举
2. 定义 `NexusError` 异常类（统一格式）
3. 添加全局异常处理器
4. 所有 HTTPException 替换为 NexusError
5. 统一响应格式：
```json
{
  "error": "TASK_NOT_FOUND",
  "message": "任务不存在",
  "details": {"task_id": "xxx"}
}
```

**Done Criteria**：
- [ ] 错误码枚举已定义
- [ ] 全局异常处理器已注册
- [ ] 所有 API 返回统一格式
- [ ] 前端无需改动（向后兼容）

**预计**：1 天

---

### Task 1-4: 添加复合索引（P1-6）

**文件**：
- `alembic/versions/xxx_add_composite_indexes.py`（Alembic 迁移）

**改动**：
1. 添加 `(project_id, status)` 复合索引
2. 添加 `(assigned_agent, status)` 复合索引
3. 添加 `(goal_id, round)` 复合索引（solutions 表）
4. 添加 `(agent_id, created_at)` 复合索引（heartbeat_logs）

**Done Criteria**：
- [ ] Alembic 迁移已创建
- [ ] 索引已添加（`PRAGMA index_list` 验证）
- [ ] 查询性能提升（EXPLAIN QUERY PLAN 验证）

**预计**：0.5 天

---

### Task 1-5: 添加外键约束（P1-7）

**文件**：
- `alembic/versions/xxx_add_fk_constraints.py`（Alembic 迁移）

**改动**：
1. `tasks.goal_id` → `goals.id` ON DELETE CASCADE
2. `tasks.project_id` → `projects.id` ON DELETE CASCADE
3. `projects.goal_id` → `goals.id` ON DELETE CASCADE
4. `task_dependencies` → `tasks` ON DELETE CASCADE

**Done Criteria**：
- [ ] Alembic 迁移已创建
- [ ] 外键约束已添加
- [ ] 删除 Goal 时，相关 Task 被级联删除
- [ ] 数据完整性验证

**预计**：0.5 天

---

### Task 1-6: N+1 查询修复（P1-3）

**文件**：
- `packages/server/src/reins/api/tasks.py`
- `packages/server/src/reins/api/goals.py`
- `packages/server/src/reins/api/projects.py`

**改动**：
1. `list_tasks` 使用 `selectinload` 预加载 dependencies
2. `list_projects` 预加载 members
3. `list_goals` 预加载 projects

**Done Criteria**：
- [ ] list_tasks 查询次数 ≤ 2（主查询 + dependencies）
- [ ] list_projects 查询次数 ≤ 2
- [ ] list_goals 查询次数 ≤ 2

**预计**：0.5 天

---

### Task 1-7: 添加分页参数（P1-9）

**文件**：
- `packages/server/src/reins/api/tasks.py`
- `packages/server/src/reins/api/goals.py`
- `packages/server/src/reins/api/projects.py`

**改动**：
1. 所有列表 API 添加 `skip` 和 `limit` 参数
2. 默认 `skip=0, limit=50`
3. 最大 `limit=200`
4. 响应中添加 `total` 字段

**Done Criteria**：
- [ ] list_tasks 支持分页
- [ ] list_goals 支持分页
- [ ] list_projects 支持分页
- [ ] 前端列表正常（手动测试）

**预计**：1 天

---

### Task 1-8: 工作流异步化（P1-10）

**文件**：
- `packages/server/src/reins/api/server.py`

**改动**：
1. `execute_workflow` 端点改为 `BackgroundTasks`
2. 返回 `{"workflow_id": "xxx", "status": "started"}`
3. 状态通过 SSE 推送

**Done Criteria**：
- [ ] execute_workflow 立即返回 200
- [ ] 工作流在后台执行
- [ ] 状态通过 SSE 推送

**预计**：1 天

---

## Phase 2：核心重构（10 天）

**目标**：server.py 拆分 + Agent 去内存 + 调度架构 + 领域模型

### Task 2-1: server.py 拆分（P0-1, M5）

**文件**：
- `packages/server/src/reins/api/server.py` → ≤ 50 行
- `packages/server/src/reins/api/legacy_routes.py`（新建）
- `packages/server/src/reins/api/internal_routes.py`（新建）
- `packages/server/src/reins/api/health.py`（新建）
- `packages/server/src/reins/api/lifespan.py`（新建）
- `packages/server/src/reins/api/agents.py`（从 server.py 拆分）

**拆分计划**：

| 目标文件 | 内容 | 预计行数 |
|----------|------|----------|
| `server.py` | create_app + 注册路由 + CORS + 异常处理 | ≤ 50 |
| `legacy_routes.py` | /goals/{id}/status, /goals/{id}/transition, /tasks/{id}/assign, /traces × 3, 全局搜索, 项目成员/进度 | ~600 |
| `agents.py` | /agents (注册/心跳/发现), /discover, /heartbeat_logs, /trigger_mode | ~400 |
| `internal_routes.py` | /internal/tasks/recover-timeout, /internal/tasks/timeout-candidates | ~150 |
| `health.py` | /health | ~50 |
| `lifespan.py` | _lifespan 函数（只保留后台任务初始化 + 数据加载） | ~300 |

**Done Criteria**：
- [ ] server.py ≤ 50 行
- [ ] 无 `@app.get/post/patch/delete` 在 server.py 中
- [ ] 所有路由正常工作（API 测试）
- [ ] 启动正常

**预计**：3 天

---

### Task 2-2: Agent 去掉内存缓存（P0-3, M4, D3）

**文件**：
- `packages/server/src/reins/manager/agent_registry.py`（大幅修改）
- `packages/server/src/reins/manager/agent_discovery.py`（修改）
- `packages/server/src/reins/background_tasks.py`（修改）
- `packages/server/src/reins/scheduler/task_assigner.py`（修改）

**改动**：
1. `AgentRegistry` 改为只读缓存（始终从 DB 刷新）
2. `HeartbeatOfflineDetector` 直接查 DB
3. `SseDisconnectDetector` 直接查 DB
4. `TaskAssigner` 直接查 DB
5. `AgentDiscovery` 直接查 DB
6. 删除 server.py 启动时的"DB → 内存"加载逻辑
7. 所有 Agent 读写走 agents 表

**Done Criteria**：
- [ ] 无 `AgentRegistry.register()` 写入内存
- [ ] 无 `AgentRegistry.heartbeat()` 更新内存
- [ ] 所有 Agent 相关操作直接读写 DB
- [ ] Agent 列表正常（手动测试）
- [ ] 心跳正常（手动测试）

**预计**：1 天

---

### Task 2-3: 调度引擎架构（P1-8, M3, D7）

**文件**：
- `packages/server/src/reins/__init__.py`（ReinsServer）
- `packages/server/src/reins/scheduler/core.py`（NexusScheduler）
- `packages/server/src/reins/scheduler/project_executor.py`（ProjectExecutor）

**改动**：
1. ReinsServer：只保留 API 层逻辑（CRUD、心跳接收、Agent 注册）
2. NexusScheduler：只做调度决策，不直接写 DB
3. ProjectExecutor：执行结果通过 `POST /api/v1/tasks/{id}/complete` 写入
4. 删除 `_mark_in_progress` 中直接写 DB（改用 API）
5. 删除 `_collect_result` 中直接写 DB（改用 API）
6. 删除 `TaskRecoverer` 中直接写 DB（改用 API）

**Done Criteria**：
- [ ] ReinsServer 不触发调度
- [ ] NexusScheduler 不直接写 DB
- [ ] 调度循环正常（日志验证）
- [ ] 任务派发正常

**预计**：2 天

---

### Task 2-4: Goal-Project-Task 1:N 关系（P1-1, M8, D1）

**文件**：
- `packages/server/src/reins/models/goal.py`（删除 project_id）
- `packages/server/src/reins/models/task.py`（删除 goal_id）
- Alembic 迁移（删除列）
- 所有引用 `Task.goal_id` 的代码
- 所有引用 `Goal.project_id` 的代码

**改动**：
1. 删除 `Goal.project_id` 列（冗余）
2. 删除 `Task.goal_id` 列（通过 project_id → goal_id 推导）
3. 确认 `Project.goal_id NOT NULL`
4. 添加 helper 方法：`Task.get_goal_id()` 通过 project_id 推导
5. 添加 helper 方法：`Goal.get_progress()` 计算所有 Project 中 Task 完成比例
6. 更新所有前端引用

**Done Criteria**：
- [ ] `Goal.project_id` 列不存在
- [ ] `Task.goal_id` 列不存在
- [ ] `Project.goal_id NOT NULL`
- [ ] 前端正常显示 Goal-Project-Task 层级
- [ ] API 正常返回数据

**预计**：2 天

---

### Task 2-5: 执行追踪清理（M6）

**文件**：
- `packages/server/src/reins/api/server.py`（删除重复 traces 路由）
- `packages/server/src/reins/api/reports.py`（统一 Trace API）

**改动**：
1. 删除 server.py 中的 3 个 traces 端点（移到 reports.py）
2. 删除重复的 list_traces 端点
3. 统一 `/api/v1/tasks/{task_id}/traces` 端点
4. 清理 `TraceRepository` 重复代码

**Done Criteria**：
- [ ] `/api/v1/traces/{task_id}` 只有一个定义
- [ ] `/api/v1/traces` 只有一个定义
- [ ] 所有 traces API 正常

**预计**：0.5 天

---

### Task 2-6: 任务依赖清理（M9）

**文件**：
- `packages/server/src/reins/models/task.py`
- `packages/server/src/reins/scheduler/dependency_resolver.py`

**改动**：
1. 删除 `Task.dependencies` ORM 关系
2. 统一使用 `task_dependencies` 表
3. 删除 `task_relations` 表（如果存在）
4. 添加循环依赖检测

**Done Criteria**：
- [ ] `Task.dependencies` 不存在
- [ ] `task_relations` 表不存在
- [ ] 依赖解析正常
- [ ] 循环依赖被检测

**预计**：0.5 天

---

## Phase 3：测试 + 收尾（5 天）

### Task 3-1: 添加核心模块单元测试（P0-6）

**文件**：
- `tests/test_scheduler.py`（新建）
- `tests/test_result_verifier.py`（新建）
- `tests/test_task_assigner.py`（新建）
- `tests/test_task_status.py`（新建）

**改动**：
1. `NexusScheduler.tick()` 测试
2. `ResultVerifier.trigger_verification()` 测试
3. `_assign_agent()` 测试
4. `TaskStatus` 枚举测试（状态转换）
5. 测试覆盖 ≥ 90%

**Done Criteria**：
- [ ] 4 个核心模块有单元测试
- [ ] `pytest tests/ -v` 全通过
- [ ] 覆盖率 ≥ 90%

**预计**：3 天

---

### Task 3-2: P2 其他项（P2-1/2/3/4/5/6）

**改动**：
1. P2-1: 魔法数字提取到 config.py
2. P2-2: 补充关键函数类型注解
3. P2-3: 日志表清理脚本
4. P2-4: 敏感数据脱敏
5. P2-5: 审计日志完善
6. P2-6: 场景匹配记录

**Done Criteria**：
- [ ] 6 项全部完成

**预计**：2 天

---

## Sprint 总工作量

| 阶段 | 天数 | 任务数 |
|------|------|--------|
| Phase 0（止血） | 2 | 4 |
| Phase 1（基础设施） | 7 | 8 |
| Phase 2（核心重构） | 10 | 6 |
| Phase 3（测试+收尾） | 5 | 2 |
| **总计** | **24** | **20** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| server.py 拆分导致路由失效 | 高 | 每个路由拆分后立即 API 测试 |
| 删除 Task.goal_id 影响前端 | 中 | 添加 `get_goal_id()` helper 兼容 |
| Agent 去内存影响心跳检测 | 高 | 先写测试验证心跳正常 |
| Alembic 迁移破坏 schema | 高 | 先备份 DB，再执行迁移 |
| 测试覆盖率不足 | 中 | 核心模块必须 90%+ |
