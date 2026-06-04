# Sprint 65: 智能体状态体系重构

> 版本: v1.0 | 日期: 2026-05-08 | 状态: 待评审

---

## 一、问题背景

### 1.1 现状问题

| 问题 | 现象 | 根因 |
|------|------|------|
| 负载数据错误 | 刚子100%无任务、蚊子30%有5个任务 | 负载注册时写死，不随任务变化 |
| 心跳不刷新状态 | 点心跳后列表状态仍为 offline | heartbeat 不更新 health_status；连通性检查阻塞刷新 |
| 状态不真实 | 所有智能体一律 offline | 双状态字段（status + health_status）不同步 |
| 心跳数据不可见 | 心跳 Tab 只显示结构化字段 | 无原始 JSON 记录 |
| model_name 不更新 | 显示注册时的旧模型 | 心跳不更新 model_name |

### 1.2 数据基线（2026-05-08 16:30）

| 智能体 | status | health_status | load | current_tasks | max_concurrent_tasks | 问题 |
|--------|--------|--------------|------|--------------|---------------------|------|
| 刚子 | offline | offline | 100 | 0 | 5 | 无任务但100%负载 |
| 谷子 | offline | offline | 66 | 0 | 5 | 无任务但66%负载 |
| 麻子 | offline | offline | 50 | 0 | 5 | 无任务但50%负载 |
| 蚊子 | offline | **online** | 30 | 5 | 5 | 5个任务但30%负载 |
| 扣子 | offline | **online** | 30 | 5 | 5 | 5个任务但30%负载 |

**核心矛盾**：`status` 和 `health_status` 是两个独立字段，heartbeat 只更新 `status`，但列表显示依赖两者一致性。

---

## 二、目标

| 目标 | 说明 |
|------|------|
| **负载实时计算** | `load = min(100, current_tasks / max_concurrent_tasks × 100)` |
| **心跳反馈真实状态** | 在线/繁忙/离线，不是无脑翻牌成 online |
| **心跳原始数据可见** | Tab 可展开查看原始 JSON |
| **model_name 实时更新** | 心跳时同步更新模型信息 |

---

## 三、负载计算方案

### 3.1 公式

```
load = min(100, (current_tasks / max_concurrent_tasks) × 100)
```

- `max_concurrent_tasks`：系统默认 5，每个智能体可独立修改
- `current_tasks`：从 tasks 表实时统计（`COUNT WHERE assigned_agent = ? AND status IN ('in_progress', 'verifying')`）
- `load` 不再手动设置，**每次心跳/任务分配/任务完成时自动重算**

### 3.2 触发时机

| 事件 | current_tasks | load |
|------|--------------|------|
| 心跳 | 从 tasks 表实时统计 | 自动计算 |
| 任务分配 | +1 | 自动计算 |
| 任务完成/超时 | -1 | 自动计算 |
| Agent 注册 | 0 | 0 |
| Agent 注销 | 0 | 0 |

### 3.3 负载颜色规则（前端）

| 负载范围 | 颜色 | 说明 |
|----------|------|------|
| 0-40% | 🟢 绿色 | 空闲 |
| 41-79% | 🟡 橙色 | 忙碌 |
| 80-100% | 🔴 红色 | 满载 |

---

## 四、心跳状态决策

### 4.1 决策逻辑

```
心跳请求
  │
  ├─ 连通性检查（agent address 可达 + 模型响应）
  │   │
  │   ├─ ✅ 通过
  │   │   │
  │   │   ├─ current_tasks >= max_concurrent_tasks → status = 'busy'
  │   │   └─ current_tasks < max_concurrent_tasks  → status = 'online'
  │   │
  │   └─ ❌ 失败
  │       │
  │       ├─ consecutive_failures >= 3 → status = 'offline'
  │       └─ consecutive_failures < 3  → status = 'online'（保持，标记告警）
  │
  └─ 同时更新 status = health_status（两字段保持一致）
```

### 4.2 状态含义

| 状态 | 含义 | 列表 Badge 颜色 |
|------|------|----------------|
| `online` | 在线待命/执行中 | 🟢 绿色 |
| `busy` | 已满载（任务数=上限） | 🟠 橙色 |
| `offline` | 离线（连续3次心跳失败） | ⚫ 灰色 |

### 4.3 连通性检查不阻塞刷新

- 心跳 API 总是返回 200（除非 agent 不存在）
- `connectivity_verified` 仅用于前端按钮显示 ✅/⚠️/❌
- **前端心跳成功后无条件刷新列表**

---

## 五、数据库变更

### 5.1 新增字段

```sql
-- 心跳日志表增加原始数据字段
ALTER TABLE heartbeat_logs ADD COLUMN raw_payload TEXT;
```

### 5.2 状态字段合并策略

**不修改表结构**，在代码层统一行为：
- `status` 和 `health_status` 同时更新为同一值
- 列表读取时优先使用 `status`
- 后续迭代可考虑删除 `health_status`

---

## 六、API 变更

### 6.1 GET /api/v1/agents（列表）

**新增返回字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `load` | int | 实时负载百分比（自动计算） |
| `current_tasks` | int | 当前执行中任务数 |
| `max_concurrent_tasks` | int | 任务上限 |
| `consecutive_offline_count` | int | 连续离线次数 |

### 6.2 POST /api/v1/agents/{id}/heartbeat（心跳）

**变更**：
- 总是返回 200（agent 不存在时返回 404）
- `connectivity_verified` 仅用于前端提示，不阻止状态更新
- 新增记录 `raw_payload` 到 heartbeat_logs

**响应示例**：

```json
{
  "success": true,
  "agent_id": "gangzi",
  "status": "online",
  "load": 0,
  "current_tasks": 0,
  "max_concurrent_tasks": 5,
  "connectivity_verified": true,
  "connectivity_check_duration_ms": 45,
  "consecutive_failures": 0,
  "assigned_tasks": []
}
```

---

## 七、前端变更

### 7.1 AgentList.tsx

| 变更 | 说明 |
|------|------|
| 心跳无条件刷新 | 删除 `if (data.connectivity_verified) fetchData()` |
| 按钮3态反馈 | ✅连通 / ⚠️告警(首次失败) / ❌失败(连续3次) |
| 状态支持 busy | Badge 增加橙色繁忙态 |
| 负载实时显示 | 进度条使用后端返回的实时 load |

### 7.2 statusMap.ts

新增 `busy` 状态映射：

```typescript
export const AGENT_STATUS_LABELS: Record<string, string> = {
  'online':  '在线',
  'idle':    '空闲',
  'busy':    '繁忙',   // 新增
  'working': '繁忙',
  'offline': '离线',
  'unknown': '未知',
}
```

### 7.3 AgentDetailModal.tsx

心跳 Tab 新增"原始数据"视图：

```
┌─────────────────────────────────┐
│ [触发日志]  [心跳日志]           │
├─────────────────────────────────┤
│ 💓 16:13:38  心跳  ✅ online    │
│    延迟: 45ms  负载: 30% 任务: 5│
│  ▶ 原始数据（可展开）            │
│  ┌───────────────────────────┐  │
│  │ {                          │  │
│  │   "status": "online",      │  │
│  │   "load": 30,              │  │
│  │   "current_tasks": 5,      │  │
│  │   "model_name": "...",     │  │
│  │   "capabilities": [...]    │  │
│  │ }                          │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

---

## 八、任务拆分

### Phase 0：迁移脚本（15min）

| Task | 内容 | 文件 | Done Criteria |
|------|------|------|---------------|
| 65.1 | heartbeat_logs 加 raw_payload 列 | `migrations/040_heartbeat_raw_payload.sql` | SQL 执行成功 |

### Phase 1：后端核心（45min）

| Task | 内容 | 文件 | Done Criteria |
|------|------|------|---------------|
| 65.3 | 负载实时计算函数 | `__init__.py`, `assignment.py` | `load = tasks/max × 100` |
| 65.4 | 心跳状态决策逻辑 | `assignment.py` | online/busy/offline 三种状态 |
| 65.5 | 心跳同时更新 status + health_status | `__init__.py` | 两字段一致 |
| 65.6 | 列表 API 补充字段 | `admin.py` | 返回 load/current_tasks/max_concurrent_tasks |
| 65.7 | 心跳记录 raw_payload | `assignment.py` | heartbeat_logs 有原始 JSON |
| 65.8 | model_name 心跳实时更新 | `__init__.py` | DB 中 model_name 更新 |

### Phase 2：前端（30min）

| Task | 内容 | 文件 | Done Criteria |
|------|------|------|---------------|
| 65.9 | 心跳无条件刷新列表 | `AgentList.tsx` | 删除 connectivity_verified 判断 |
| 65.10 | 心跳按钮3态反馈 | `AgentList.tsx` | ✅/⚠️/❌ 三种颜色 |
| 65.11 | 列表支持 busy 态 | `AgentList.tsx` + `statusMap.ts` | 橙色 Badge |
| 65.12 | 负载进度条实时值 | `AgentList.tsx` | 颜色随负载变化 |

### Phase 3：心跳 Tab 原始 JSON（15min）

| Task | 内容 | 文件 | Done Criteria |
|------|------|------|---------------|
| 65.13 | 心跳 Tab 原始数据视图 | `AgentDetailModal.tsx` | 可折叠 JSON 显示 |

---

## 九、验收标准

### 编译验证
- [ ] `npx tsc --noEmit` 0 errors
- [ ] `pytest` 通过（如有）

### API 验证
- [ ] `GET /api/v1/agents` 返回 load、current_tasks、max_concurrent_tasks
- [ ] `POST /api/v1/agents/{id}/heartbeat` 返回完整状态（含 connectivity_verified）
- [ ] heartbeat_logs 表有 raw_payload 字段

### 页面验证
- [ ] 5 个智能体列表状态正确（根据实际负载）
- [ ] 点击心跳后状态实时更新（online/busy/offline）
- [ ] 负载百分比 = current_tasks / max_concurrent_tasks × 100
- [ ] 繁忙态显示橙色 Badge
- [ ] 心跳 Tab 可展开查看原始 JSON
- [ ] 页面不白屏，关键元素可见

---

## 十、预期收益

| 指标 | 修改前 | 修改后 |
|------|--------|--------|
| 负载准确性 | 注册时写死，永不更新 | 实时计算，动态反映 |
| 状态准确性 | 一律 offline | 真实反馈 online/busy/offline |
| 心跳可用性 | 点心跳无反应 | 即时刷新 + 3态反馈 |
| 数据透明度 | 只显示结构化字段 | 可看原始 JSON |
| 运维效率 | 查 DB 猜状态 | 列表一目了然 |
