# Sprint 5 详细任务拆分

**Sprint**: 5
**主题**: 生产级基础设施 + 多元触发架构
**版本**: v1.0
**制定日期**: 2026-04-11

---

## P5-01：EventBus 抽象

**任务**: 设计并实现统一的 EventBus，支持 SSE/Poll 两种 Adapter

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-01-01 | **EventBus 接口设计** - 定义 IEventBus 接口，包含 `subscribe(agent_id, event_types)` / `unsubscribe()` / `publish(event)` | - | 接口文档完成 |
| P5-01-02 | **Event 类型定义** - 定义 EventType 枚举（task_assigned / task_completed / dispute_raised / agent_status_changed / goal_updated） | - | 枚举完整，有类型定义 |
| P5-01-03 | **SSE Adapter 实现** - 实现 SseEventAdapter，支持多个 Agent 订阅 | P5-01-01, P5-01-02 | Agent 可通过 SSE 订阅事件 |
| P5-01-04 | **Polling Adapter 实现** - 实现 PollingEventAdapter，支持轮询拉取未读事件 | P5-01-01, P5-01-02 | Agent 可通过轮询获取事件 |
| P5-01-05 | **Adapter 切换逻辑** - 实现 `get_adapter(agent_id)` 根据 Agent 的 trigger_mode 返回对应 Adapter | P5-01-03, P5-01-04 | 切换无感，代码可扩展 |
| P5-01-06 | **Event 持久化** - Event 写入 DB（polling 模式需要），支持分页查询 | P5-01-01 | 事件不丢失，可追溯 |

**技术方案**:
```python
class IEventBus(ABC):
    @abstractmethod
    def subscribe(self, agent_id: str, event_types: List[EventType]):
        pass
    
    @abstractmethod
    def unsubscribe(self, agent_id: str):
        pass
    
    @abstractmethod
    def publish(self, event: Event):
        pass

class EventBus:
    def __init__(self):
        self._adapters: Dict[str, IEventAdapter] = {}
        self._subscribers: Dict[str, Set[EventType]] = {}
    
    def get_adapter(self, agent_id: str, trigger_mode: str) -> IEventAdapter:
        if trigger_mode == "sse":
            return self._sse_adapter
        return self._polling_adapter
```

---

## P5-02：SSE 实时推送

**任务**: Agent 可订阅 SSE 实时接收任务推送（秒级响应）

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-02-01 | **SSE API 端点设计** - `GET /events/stream?agent_id=X` 流式返回事件 | P5-01-03 | 端点可访问 |
| P5-02-02 | **SSE 连接管理** - 支持多 Agent 并发 SSE 连接，连接超时/断开处理 | P5-02-01 | 10个Agent并发连接稳定 |
| P5-02-03 | **Task 推送集成** - Task 创建/变更时自动通过 SSE 推送给相关 Agent | P5-01-03 | Task 变更 < 1秒到达 Agent |
| P5-02-04 | **Dispute 推送集成** - Dispute 创建时立即推送给相关 Agent | P5-01-03 | Dispute 创建 < 1秒推送 |
| P5-02-05 | **前端 SSE 集成** - ExecutionMonitoring 页面使用 SSE 而非轮询 | P5-02-01 | 页面实时更新，无闪烁 |
| P5-02-06 | **SSE 心跳** - 每 15 秒发送 comment 保持连接活跃 | P5-02-02 | 连接 5 分钟不断开 |

**API 设计**:
```
GET /api/v1/events/stream
Headers:
  Accept: text/event-stream
  X-Agent-ID: agent-001

Response (SSE stream):
event: task_assigned
data: {"event_id":"e1","task_id":"t1","goal_id":"g1","timestamp":"..."}

event: dispute_raised
data: {"event_id":"e2","dispute_id":"d1","type":"resource_conflict",...}
```

---

## P5-03：Task 完整状态机

**任务**: todo → in_progress → blocked → done / cancelled

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-03-01 | **Task 状态枚举定义** - 7个状态：backlog / todo / in_progress / in_review / blocked / done / cancelled | - | 枚举完整 |
| P5-03-02 | **状态转换规则** - 定义每个状态可转换到哪些状态，拒绝非法转换 | P5-03-01 | 非法转换返回 400 |
| P5-03-03 | **状态副作用** - 状态变更时自动设置：startedAt / completedAt / cancelledAt | P5-03-01 | 时间戳正确 |
| P5-03-04 | **Task 列表过滤** - `GET /tasks?status=in_progress` 按状态筛选 | P5-03-01 | 筛选正确 |
| P5-03-05 | **Task 批量操作** - `PATCH /tasks/batch` 批量状态变更（用于人工修正） | P5-03-02 | 批量更新成功 |
| P5-03-06 | **Task 阻塞机制** - Task 被 blocked 时可设置 blocked_reason，上游解锁时自动解除 | P5-03-01 | 阻塞/解锁逻辑正确 |
| P5-03-07 | **Task 历史记录** - 状态变更写入 activity_log | P5-03-03 | 历史可查 |

**状态转换图**:
```
backlog → todo → in_progress → in_review → done
                ↓               ↓
              blocked       blocked
                ↓               ↓
              (解锁) → in_progress
                               ↓
                            cancelled
```

---

## P5-04：API 认证

**任务**: Bearer token 认证

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-04-01 | **Token 模型设计** - Token 表：token_id / hash / user_id / agent_id / expires_at / created_at | - | 表结构设计完成 |
| P5-04-02 | **Token 生成 API** - `POST /auth/token` 生成 Bearer token（支持 user/agent 类型） | P5-04-01 | 返回 token |
| P5-04-03 | **Token 验证中间件** - FastAPI 依赖项 `verify_token()` 验证 Authorization header | P5-04-02 | 无 token 返回 401 |
| P5-04-04 | **Token 刷新** - `POST /auth/refresh` 刷新 token（有效期延长） | P5-04-02 | 新 token 可用 |
| P5-04-05 | **Token 撤销** - `DELETE /auth/token` 撤销 token | P5-04-02 | 撤销后立即失效 |
| P5-04-06 | **Agent Token** - Agent 注册时自动生成 token，支持 API Key 方式调用 | P5-04-02 | Agent 可用 token 调用 |
| P5-04-07 | **敏感端点标记** - 定义哪些端点需要认证，哪些可选 | P5-04-03 | 认证逻辑覆盖所有敏感端点 |

**API 设计**:
```
POST /api/v1/auth/token
{
  "type": "agent",  // or "user"
  "agent_id": "agent-001",
  "name": "Agent 1"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2026-04-12T00:00:00Z"
}

GET /api/v1/tasks
Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## P5-05：Agent 心跳增强

**任务**: 离线检测、自动标记 offline，支持 trigger_mode 声明

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-05-01 | **trigger_mode 字段** - Agent 表增加 trigger_mode 字段（sse/poll） | - | 字段存在 |
| P5-05-02 | **Agent 注册增强** - `POST /agents` 支持 trigger_mode 和 poll_interval 参数 | P5-05-01 | 注册时可指定 |
| P5-05-03 | **心跳离线检测** - 后台任务检测超过 30 秒无心跳的 Agent，标记为 offline | P5-04 | 30秒内无心跳自动 offline |
| P5-05-04 | **Agent 状态变更事件** - Agent 变为 offline 时发布 Event 到 EventBus | P5-01-03 | 事件可推送 |
| P5-05-05 | **心跳历史** - 心跳记录写入 DB（heartbeat_logs），支持查询心跳历史 | P5-05-03 | 历史可查 |
| P5-05-06 | **poll_interval 配置** - Agent 注册时指定 poll_interval_seconds，轮询 Agent 按此间隔拉取 | P5-05-01 | 间隔生效 |

---

## P5-06：Goal 状态机

**任务**: created → planned → in_progress → completed/failed

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-06-01 | **Goal 状态枚举** - 5个状态：draft / planned / in_progress / completed / failed | - | 枚举完整 |
| P5-06-02 | **状态转换规则** - 定义每个状态可转换到哪些状态 | P5-06-01 | 非法转换返回 400 |
| P5-06-03 | **自动触发** - Goal 状态变更时自动更新关联 Task 的状态 | P5-06-01 | 联动正确 |
| P5-06-04 | **Goal 完成条件** - 所有 child goals + 所有 tasks done 时，Goal 可标记 completed | P5-06-01 | 完成条件正确 |
| P5-06-05 | **Goal 失败条件** - 有 Task failed 且无法恢复时，Goal 标记 failed | P5-06-01 | 失败判断正确 |

---

## P5-07：Polling 降级

**任务**: SSE 不可用时自动降级到轮询

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-07-01 | **Polling API** - `GET /events/pull?agent_id=X&since=timestamp` 拉取未读事件 | P5-01-04 | 返回未读事件列表 |
| P5-07-02 | **SSE 断连检测** - 检测 SSE 连接断开（心跳超时） | P5-02-02 | 断开可检测 |
| P5-07-03 | **降级触发器** - SSE 断连后自动将 Agent 的 trigger_mode 切换为 poll | P5-07-02 | 切换无感 |
| P5-07-04 | **降级通知** - 降级发生时通过轮询响应告知 Agent | P5-07-03 | Agent 知道已降级 |
| P5-07-05 | **SSE 恢复检测** - Agent 重连 SSE 成功时自动切回 trigger_mode=sse | P5-02-02 | 可恢复 |

---

## P5-08：执行监控 Trace 增强

**任务**: 实时显示步骤耗时、agent归属

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-08-01 | **Trace 存储** - TraceEvent 持久化到 DB，不只是内存 | P5-01-06 | Trace 不丢失 |
| P5-08-02 | **步骤耗时计算** - 从 Trace 计算每个步骤的实际耗时 | P5-08-01 | 耗时显示正确 |
| P5-08-03 | **Agent 归属** - TraceEvent 关联 agent_id，显示执行者 | P5-08-01 | 归属正确 |
| P5-08-04 | **时间线渲染** - ExecutionMonitoring 页面渲染真实 Trace 时间线 | P5-08-02, P5-02-05 | 时间线正确 |
| P5-08-05 | **步骤状态联动** - Workflow step 状态 = Trace 最新状态 | P5-08-01 | 状态同步 |

---

## P5-09：错误处理规范化

**任务**: 统一错误码、错误返回格式

**子任务**:

| # | 子任务 | 依赖 | 验收标准 |
|---|--------|------|---------|
| P5-09-01 | **错误码定义** - 定义 ErrorCode 枚举（1001-1999 参数错误，2001-2999 业务错误，3001-3999 系统错误） | - | 枚举完整 |
| P5-09-02 | **错误响应格式** - 统一 `{code, message, details}` 格式 | P5-09-01 | 格式统一 |
| P5-09-03 | **HTTP 状态码映射** - 400/401/403/404/500 对应不同错误类型 | P5-09-01 | 状态码正确 |
| P5-09-04 | **全局异常处理器** - FastAPI 异常处理器统一捕获并返回格式化错误 | P5-09-02 | 无原始异常泄露 |
| P5-09-05 | **业务异常类** - 定义 `TaskNotFoundError` / `AgentOfflineError` / `InvalidStateTransitionError` 等 | P5-09-01 | 异常类完整 |

**错误响应格式**:
```json
{
  "code": 2001,
  "message": "无效的状态转换",
  "details": {
    "current_state": "done",
    "requested_state": "in_progress",
    "allowed_states": []
  }
}
```

---

## Sprint 5 验收测试用例

| # | 测试用例 | 验证标准 |
|---|---------|---------|
| T5-01 | Agent 注册 SSE 模式，收到 Task 推送 | < 1秒 |
| T5-02 | SSE 断连后，Agent 降级到轮询并正常获取事件 | 降级无感 |
| T5-03 | Task 状态从 todo → in_progress → done 完整流程 | 状态正确 |
| T6-04 | API 调用不带 Bearer token | 返回 401 |
| T5-05 | Agent 30秒无心跳，状态变为 offline | 状态正确 |
| T6-06 | Goal 所有 Task done 时，Goal 自动 completed | 自动完成 |
| T5-07 | 执行监控页面实时显示 Trace 时间线 | 无需刷新 |

---

## 技术债务清理

| # | 任务 | 说明 |
|---|------|------|
| TD-01 | 清理 tracker_sync.py | 重命名为 execution_tracker.py 或合并到 tracker |
| TD-02 | 统一 DB 模型命名 | SqlXxx → XxxRow 或统一用现有风格 |
| TD-03 | 移除 mock 数据 | Sprint 4 的 mock 全部替换为真实 API |
