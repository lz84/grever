# Sprint 54: Human-in-the-Loop 人在环路

## 目标

让 Agent 在执行任务时可以请求人类输入，系统记录请求并通知人类，人类提交后自动解锁下游任务。

## 实施记录

### 2026-05-05 凌晨 — Vite Proxy 500 修复 + 详情页重写

#### 问题 1: Vite Proxy 500 错误

**症状**: 人类输入列表页通过 Vite proxy (5173→8092) 请求 `/api/v1/human-input/pending` 返回 500，但直接访问后端 8092 也返回 500。

**根因**: 旧后端进程 (PID 38544) 在 `get_pending_requests` 中，`context` 字段从 DB 读取为 JSON 字符串（如 `'{"test":"context"}'`），`json.loads` 解析后传给 Pydantic `HumanInputRequest` 模型时，Pydantic v2 严格校验 `Optional[Dict[str, Any]]` 类型，但某些情况下解析失败或传递了字符串导致 validation error。

**修复**: 
- 杀掉旧后端进程 (PID 38544, 73144)
- 在 8092 端口重启新后端，`context` 字段正确解析为 dict
- Vite proxy 恢复正常，列表页返回 6 条待处理请求

#### 问题 2: 详情页用户体验差（用户反馈三个问题）

用户反馈：
1. "第一没有问题产生的原因，怎么产生的，需要我输入什么"
2. "第二我不知道我该做什么"
3. "第三操作按钮有确认和取消，但是下面让我输入拒绝原因，是什么意思"

**修复 — 详情页重写**:
- 新增三个解释性区域（蓝/黄/绿卡片）：
  - 📋 **这是什么请求？** — 显示 description + 关联任务 ID
  - ❓ **为什么需要你？** — 结合 input_type 生成通俗解释，优先使用 description 字段
  - ✅ **你需要做什么？** — 明确告诉用户该做什么，以及操作后果
- 新增 ⚡ **做出决定** 区域 — 按钮清晰可见，根据 input_type 显示不同按钮文字
- 拒绝原因改为**条件显示** — 只有点击"否决"后才展开红色区域的拒绝原因输入框，解决了"按钮是确认/取消但下面常驻拒绝原因输入框"的逻辑混乱
- 列表页点击项时调 `/api/v1/human-input/{id}` 获取完整详情，而非仅用列表数据

**修改文件**: `packages/ui/src/pages/HumanInputPage.tsx`

**新增函数**: `getContextExplanation()` — 根据 input_type 生成三段式解释（原因/行动/后果）

### 2026-05-04 晚间 — Sprint 56 完成

**完成 3/3 任务**:
- waiting_human 状态实现
- 飞书通知机制
- 超时处理

---

### Sprint 55 需求梳理

基于 2026-05-04 的 Sprint 55 需求分析文档，将需求拆分为具体的 Sprint 任务。

### 前端优化（2026-05-05 凌晨完成）

**Vite Proxy 500 修复**:
- 杀掉旧后端进程 (PID 38544, 73144)，重启新后端到 8092 端口
- `context` 字段从 DB JSON 字符串正确解析为 dict，Pydantic 校验通过
- 列表页返回 6 条待处理请求（3 条确认 + 3 条审批）

**详情页重写**:
- 新增三段式解释区域（📋 是什么 / ❓ 为什么 / ✅ 做什么）
- 拒绝原因改为条件显示（点击否决后才出现）
- 列表页点击项时调详情 API 获取完整数据

## 实施记录

### 2026-05-05 凌晨 — Vite Proxy 500 修复 + 详情页重写

**问题 1: Vite Proxy 500 错误**

**症状**: `/human-input` 列表页数据为空，Vite proxy 返回 500。

**根因**: 旧后端进程 (PID 38544) 在 `get_pending_requests` 中，`context` 字段从 DB 读取为 JSON 字符串，Pydantic v2 严格校验 `Optional[Dict[str, Any]]` 类型失败。

**修复**: 杀掉旧进程，在 8092 端口重启新后端。

**问题 2: 详情页用户体验差**

**用户反馈**:
1. "没有问题产生的原因，怎么产生的，需要我输入什么"
2. "不知道我该做什么"
3. "操作按钮有确认和取消，但是下面让我输入拒绝原因"

**修复**: 重写详情页，新增三段式解释区域（是什么/为什么/做什么），拒绝原因改为条件显示。

### 2026-05-04 晚间 — Sprint 56 完成

**完成 3/3 任务**: waiting_human 状态 + 飞书通知 + 超时处理

---

## 设计原则

1. **不阻塞 Agent session** — Agent 报"需要人类输入"后直接 done，不挂在那里等
2. **场景模板驱动 80%** — 场景模板预定义 human_input_schema，直接渲染
3. **自由文本兜底 20%** — Agent 临时声明的字段用文本框 + LLM 提取
4. **继承 Verifier 机制** — 人类提交的内容也可以走验证流程

## 技术方案

### DB 变更

**1. 新状态** `waiting_human`（加到 TaskStatus 枚举）

**2. 新表** `human_input_requests`:
```sql
CREATE TABLE human_input_requests (
    id TEXT PRIMARY KEY,           -- 'hi-xxxxx'
    task_id TEXT NOT NULL,         -- 关联任务
    input_type TEXT,               -- 'template' | 'agent_declared' | 'free_text'
    schema_json TEXT,              -- 字段定义 JSON (模板预定义或 Agent 声明)
    status TEXT DEFAULT 'pending', -- pending / submitted / rejected
    input_data TEXT,               -- 人类提交的输入 JSON
    submitted_by TEXT,             -- 提交人 ID
    submitted_at TEXT,             -- 提交时间
    rejected_reason TEXT,          -- 打回原因
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

### API 端点

```
POST /api/v1/tasks/{task_id}/request-human-input    -- Agent 声明需要人类输入
GET  /api/v1/human-input/pending                     -- 查询待处理的输入请求
GET  /api/v1/human-input/{input_id}                  -- 获取输入请求详情
POST /api/v1/human-input/{input_id}/submit           -- 人类提交输入
POST /api/v1/human-input/{input_id}/reject           -- 打回重填
```

### 业务流

```
1. Agent 执行任务，发现需要人类输入
   ↓
2. Agent 在 result 中标记:
   {
     "needs_human_input": true,
     "input_type": "template",         // 或 "agent_declared" / "free_text"
     "schema": {"field1": "text", ...},
     "description": "需要现场报告"
   }
   ↓
3. complete_task API 检测到 needs_human_input
   → 创建 human_input_requests 记录 (status=pending)
   → task 状态保持 done（Agent 不阻塞）
   → 下游任务依赖于此 input 完成的保持 blocked
   → 触发通知（飞书消息）
   ↓
4. 人类收到通知，打开 Nexus → 看到待处理输入请求
   → 填写表单（场景模板驱动）或写自由文本
   → 提交
   ↓
5. POST /human-input/{id}/submit
   → 更新 human_input_requests (status=submitted)
   → 触发下游任务解锁（依赖此 input 的任务变 todo）
   → 可选：触发下一个 Agent 执行
```

### Agent 输出解析

在 complete_task API 中增加一步：

```python
# 解析 Agent result，检查是否有 needs_human_input
result_data = _parse_agent_result(request.result)
if result_data.get("needs_human_input"):
    # 创建人类输入请求
    _create_human_input_request(
        task_id=task_id,
        input_type=result_data.get("input_type", "free_text"),
        schema=result_data.get("schema", {}),
        description=result_data.get("description", ""),
    )
    # Agent 这边标记为 done
    task.status = "done"
    # 下游依赖此任务的，如果依赖的是人类输入部分 → 保持 blocked
    # 实现方式：下游任务的 dependency 指向一个新创建的 "等待人类输入" 子任务
```

### 下游任务解锁

复用 DependencyResolver，但增加一个变体：

```python
def unlock_on_human_input(self, input_id: str) -> List[str]:
    """
    人类提交输入后调用
    1. 找到关联的 task（该 task 已完成）
    2. 检查依赖此 task 的下游任务
    3. 依赖全部满足 → 解锁
    """
```

## Sprint 任务拆分

| Sprint | 任务 | 依赖 | 验收标准 |
|--------|------|------|----------|
| Sprint 54-T1 | DB 迁移: waiting_human 状态 + human_input_requests 表 | - | PRAGMA 看到新表新列 |
| Sprint 54-T2 | HumanInputRequest ORM model | T1 | model 导入无报错 |
| Sprint 54-T3 | Agent 输出解析: needs_human_input 检测 | - | JSON 解析 + 字段提取 |
| Sprint 54-T4 | complete_task 集成: 检测到 human input → 创建请求 | T2, T3 | API 测试通过 |
| Sprint 54-T5 | API 端点: request / submit / reject / pending 查询 | T1, T2 | curl 验证全部 200 |
| Sprint 54-T6 | DependencyResolver 扩展: unlock_on_human_input | T1 | 下游任务自动解锁 |
| Sprint 54-T7 | E2E 测试: 完整人在环路流程 | T4, T5, T6 | 测试脚本全通过 |
