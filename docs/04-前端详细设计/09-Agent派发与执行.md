# Agent 派发与执行 - 详细设计

> 覆盖 Sprint 9 第1、2步：Agent 派发机制 + 结果回收
> 这是 Nexus 替代 Paperclip 的核心能力

---

## 一、整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                        Nexus 调度中心                        │
│                                                              │
│  目标创建 → 自动分解 → 任务队列 → [派发] → Agent 执行 → [回收] │
│                                                              │
│                    ↕ 反馈闭环                                 │
│              场景库 ← 执行结果分析 ← 场景数据更新              │
└──────────────────────────────────────────────────────────────┘
```

## 二、Agent 派发机制（第1步）

### 2.1 派发流程

```
1. 任务进入队列（status = 'pending'）
2. Agent heartbeat 时拉取任务
   - POST /api/v1/agents/{agent_id}/heartbeat
   - 返回：分配给该 agent 的 pending 任务列表
3. Agent 接收任务上下文
   - 任务描述、目标信息、关联场景
   - 场景库中的标准操作指南（如果有）
4. Agent 开始执行
   - POST /api/v1/tasks/{task_id}/start
   - 状态变为 'in_progress'
```

### 2.2 Heartbeat API 增强

**端点**：`POST /api/v1/agents/{agent_id}/heartbeat`

**当前**：只更新 last_heartbeat 和 status

**增强后**：
- 返回分配给该 agent 的 pending 任务
- 返回任务上下文（目标描述、场景指南等）
- 返回该 agent 的负载上限检查

**请求体**：
```json
{
  "status": "online",
  "load": 60,
  "current_tasks": 1,
  "capabilities": ["coding", "testing"]
}
```

**响应体**：
```json
{
  "success": true,
  "assigned_tasks": [
    {
      "id": "task-001",
      "title": "修复用户登录 bug",
      "description": "...",
      "goal_id": "goal-001",
      "goal_title": "系统稳定性提升",
      "priority": "high",
      "context": {
        "scenario_guide": "标准 bug 修复流程...",
        "related_files": ["src/auth/login.ts"],
        "previous_attempts": []
      }
    }
  ],
  "load_limit_warning": false
}
```

### 2.3 任务分配逻辑

**分配策略**：
1. 按能力匹配：任务需要的能力 ⊆ Agent 能力集
2. 按负载均衡：选择当前负载最低的合格 Agent
3. 按优先级：高优先级任务优先分配

**后端实现**：`reins/api/assignment.py`

```python
def assign_pending_tasks(agent_id: str) -> List[Task]:
    """分配 pending 任务给指定 agent"""
    agent = get_agent(agent_id)
    pending_tasks = get_pending_tasks()
    
    # 能力匹配
    matched = [t for t in pending_tasks if matches_capabilities(t, agent)]
    
    # 按优先级排序
    matched.sort(key=lambda t: priority_order(t.priority))
    
    # 负载检查
    available_slots = agent.load_limit - agent.current_tasks
    return matched[:available_slots]
```

### 2.4 任务上下文注入

**端点**：`GET /api/v1/tasks/{task_id}/context`

**返回内容**：
- 任务所属目标的信息
- 关联场景的标准操作指南（如果有）
- 历史执行记录（类似任务之前怎么做的）
- 相关文件/代码上下文

---

## 三、执行结果回收（第2步）

### 3.1 结果上报流程

```
Agent 执行完成 → POST /api/v1/tasks/{task_id}/complete
  ↓
更新 Task 状态 → done/failed
  ↓
触发场景库反馈 → POST /api/v1/scenarios/{scenario_id}/feedback
  ↓
更新目标进度 → 检查 Goal 是否完成
  ↓
如果 Goal 完成 → 触发 Goal 完成回调
```

### 3.2 任务完成 API

**端点**：`POST /api/v1/tasks/{task_id}/complete`

**请求体**：
```json
{
  "status": "done",
  "result": "修复了登录验证逻辑...",
  "artifacts": ["src/auth/login.ts"],
  "duration_ms": 1800000,
  "confidence": 0.95,
  "issues_encountered": ["初始代码结构混乱"]
}
```

**响应体**：
```json
{
  "success": true,
  "task_id": "task-001",
  "goal_progress": {
    "goal_id": "goal-001",
    "completed_tasks": 5,
    "total_tasks": 8,
    "progress_percent": 62.5
  },
  "scenario_feedback_triggered": true
}
```

### 3.3 任务失败 API

**端点**：`POST /api/v1/tasks/{task_id}/fail`

**请求体**：
```json
{
  "error_type": "compilation_error",
  "error_message": "Type error: ...",
  "retry_count": 1,
  "max_retries": 3
}
```

### 3.4 Issue 状态自动更新

当 Task 完成时：
1. 更新 Task 状态
2. 更新 Goal 进度
3. 如果所有 Task 完成 → Goal 状态变为 'completed'
4. 触发场景库反馈

---

## 四、场景库反馈闭环（第3步）

### 4.1 反馈触发时机

- 任务完成时自动触发
- 目标完成时批量触发
- 手动触发（管理员操作）

### 4.2 反馈数据

```json
{
  "scenario_id": "scenario-001",
  "execution_data": {
    "task_id": "task-001",
    "goal_id": "goal-001",
    "status": "done",
    "duration_ms": 1800000,
    "quality_score": 0.95,
    "issues": [],
    "improvements": ["优化了代码结构"]
  }
}
```

### 4.3 场景数据更新

**更新内容**：
- 总执行次数 +1
- 成功/失败计数更新
- 平均耗时重新计算
- 如果质量评分 > 阈值 → 场景版本升级

**版本升级规则**：
- 连续 3 次高质量执行（>0.9）→ 版本号 +0.1
- 出现严重问题 → 标记为"需要审查"

### 4.4 反馈 API

**端点**：`POST /api/v1/scenarios/{scenario_id}/feedback`（已定义，待实现）

**请求体**：
```json
{
  "workflow_id": "workflow-001",
  "task_id": "task-001",
  "status": "completed",
  "duration_ms": 1800000,
  "steps_completed": 5,
  "steps_total": 5,
  "conflicts_count": 1,
  "quality_metrics": {
    "accuracy": 0.95,
    "efficiency": 0.88,
    "stability": 0.92
  }
}
```

---

## 五、全链路 E2E 测试 + 迁移工具（第5步）

### 5.1 E2E 测试场景

**测试用例 1：完整任务生命周期**
```
1. 创建目标 → 自动分解为任务
2. Agent heartbeat 拉取任务
3. Agent 执行任务并上报完成
4. 验证任务状态更新
5. 验证目标进度更新
6. 验证场景库反馈触发
```

**测试用例 2：多 Agent 协同**
```
1. 创建包含多个任务的目标
2. 多个 Agent 同时 heartbeat
3. 验证任务正确分配到不同 Agent
4. 验证所有任务完成后目标完成
```

**测试用例 3：任务失败重试**
```
1. Agent 执行任务失败
2. 验证任务状态变为 failed
3. 验证重试机制触发
4. 验证超过最大重试次数后标记为阻塞
```

### 5.2 Paperclip 迁移工具

**迁移内容**：
- Issues → Goals/Tasks
- Agents → Agents
- 执行历史 → 执行记录

**迁移脚本**：`scripts/migrate_paperclip.py`

```python
def migrate_issues_to_goals():
    """将 Paperclip Issues 迁移为 Nexus Goals/Tasks"""
    paperclip_issues = fetch_paperclip_issues()
    for issue in paperclip_issues:
        if issue.is_goal:
            create_goal(issue)
        else:
            create_task(issue)
```

**迁移验证**：
- 数据完整性检查
- 关联关系验证
- 抽样执行验证

---

## 六、前端适配

### 6.1 执行状态实时更新

**WebSocket/SSE 推送**：
- 任务状态变更推送
- 目标进度更新推送
- Agent 状态变更推送

### 6.2 执行监控页面增强

**新增内容**：
- 实时任务队列显示
- Agent 当前执行任务显示
- 执行日志实时流

### 6.3 任务详情页

**新增字段**：
- 执行状态（pending/in_progress/done/failed/blocked）
- 执行 Agent
- 开始/完成时间
- 执行结果摘要
- 重试次数

---

**文档版本**: v1.0
**日期**: 2026-04-15

---

## 六、补充：缺口任务详细设计

### 6.1 场景库反馈闭环完善（MAK-232）

**反馈触发时机**：
- 任务完成时自动触发（单个任务）
- 目标完成时批量触发（所有关联任务）
- 手动触发（管理员操作）

**场景数据更新**：
- total_executions += 1
- success_count / failed_count 更新
- avg_duration_ms 重新计算
- min_duration_ms / max_duration_ms 更新
- avg_conflicts 更新

**版本升级规则**：
- 连续 3 次高质量执行（quality_score > 0.9）→ version += 0.1
- 出现严重问题（error_type 包含 critical）→ status = 'needs_review'

### 6.2 工作流引擎与派发集成（MAK-233）

**Workflow 激活流程**：
1. POST /workflows/{id}/activate
2. 获取 workflow 的所有 steps
3. 为每个 step 创建 Task（status = 'pending'）
4. Task 自动进入派发队列
5. Agent heartbeat 时领取任务

**Task 完成回调**：
1. Task 完成 → 更新对应 Workflow step 状态
2. 检查所有 steps 是否完成
3. 全部完成 → Workflow status = 'completed'
4. 部分失败 → 触发重试或标记 blocked

### 6.3 前端执行监控增强（MAK-234）

**新增组件**：
- TaskQueuePanel：显示 pending/in_progress 任务队列
- AgentTaskCard：显示 Agent 当前正在执行的任务
- ExecutionLogStream：SSE 推送的执行日志实时流
- TaskDetailPanel：任务详情（状态/Agent/时间/结果/重试次数）

**路由**：
- /executions/queue → 实时任务队列
- /executions/agents → Agent 执行状态
- /executions/logs → 执行日志流

### 6.4 任务失败重试机制（MAK-235）

**重试策略**：
- 失败后自动重新加入派发队列（delay = 30s * retry_count）
- 最大重试次数：3 次（可配置）
- 超过重试次数：status = 'blocked'，需要人工干预
- 失败原因记录：error_type, error_message, stack_trace

**API**：
- POST /tasks/{id}/retry → 手动重试
- GET /tasks/{id}/failure-log → 查看失败历史

### 6.5 前端目标自动分解 UI（MAK-236）

**新建页面**：/goals/{id}/decompose-preview

**功能**：
- 显示 LLM 分解结果（任务列表预览）
- 支持手动编辑任务（增删改）
- 支持调整任务依赖关系
- 确认后提交 → 创建 Tasks 并加入派发队列

### 6.6 Agent 负载管理与限流（MAK-237）

**负载配置**：
- max_concurrent_tasks：最大并发任务数（默认 5）
- load_threshold：负载阈值（超过后拒绝新任务）
- recovery_threshold：恢复阈值（低于后恢复分配）

**API**：
- GET /agents/{id}/load → 查看当前负载
- PUT /agents/{id}/config → 更新负载配置
- GET /agents/{id}/pending-tasks → 查看待领取任务

**离线处理**：
- Agent 超过 5 分钟未 heartbeat → 标记 offline
- 该 Agent 的 pending 任务重新分配给其他 Agent
- 该 Agent 的 in_progress 任务标记为 blocked
