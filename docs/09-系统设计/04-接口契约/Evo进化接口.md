# Evo 进化接口

**版本**: v1.1
**作者**: 刚子
**日期**: 2026-05-27
**状态**: 草稿
**关联需求**: Nexus 进化领域
**变更记录**:
- v1.0 2026-05-27 刚子 初始版本
- v1.1 2026-06-01 刚子 Sprint 104: 接口统一为 GEP 协议（pattern → gene，solidified_pattern → capsule，weight_update → evolution_event）

---

## 一、概述

### 1.1 接口范围

本文档定义 Evo 进化引擎相关的所有 API 接口，包括经验提取、能力进化、A2A 通信和信念管理。

### 1.2 Evo 核心概念

| 概念 | 说明 |
|------|------|
| **Gene（基因）** | 可复用技能/策略的标准化描述，类似 DNA |
| **Capsule（记忆体）** | 一次完整执行过程的记录 |
| **Event（进化事件）** | 进化过程的元数据记录 |
| **A2A Hub** | Agent 间传递经验/信念/模式的通信协议 |

### 1.3 变异类型

| 类型 | 说明 | 风险等级 |
|------|------|---------|
| `repair` | 修复错误 | 低 |
| `optimize` | 优化性能 | 低 |
| `innovate` | 探索新策略 | 中/高 |

---

## 二、接口清单总表

### 2.1 基因管理（GEP）

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 提取 Gene | POST | `/api/v1/evo/genes/extract` | 从执行记录中提取 Gene |
| 查询 Gene 列表 | GET | `/api/v1/evo/genes` | 获取所有已提取的 Gene |
| 查询 Gene 详情 | GET | `/api/v1/evo/genes/{gene_id}` | 获取单个 Gene 详情 |
| 触发技能提炼 | POST | `/api/v1/evo/distill` | 手动触发技能提炼任务 |
| 更新 Gene 支持度 | PUT | `/api/v1/evo/genes/{gene_id}/support` | 更新 Gene 支持/反对计数 |

### 2.2 Capsule 管理（GEP）

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询 Capsule 列表 | GET | `/api/v1/evo/capsules` | 获取所有已固化的 Capsule |
| 查询 Capsule 详情 | GET | `/api/v1/evo/capsules/{capsule_id}` | 获取单个 Capsule 详情 |
| 提升 Capsule 状态 | PUT | `/api/v1/evo/capsules/{id}/promote` | draft→validated→solidified |
| 废弃 Capsule | PUT | `/api/v1/evo/capsules/{id}/deprecate` | 标记为已废弃 |
| 固化能力变更 | POST | `/api/v1/evo/solidify` | 将成功的变更固化为 Capsule |

### 2.3 EvolutionEvent 管理（GEP）

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询进化事件 | GET | `/api/v1/evo/evolution-events` | 获取进化事件列表 |
| 查询进化事件详情 | GET | `/api/v1/evo/evolution-events/{event_id}` | 获取单个事件详情 |
| 进化能力 | POST | `/api/v1/evo/evolve-capabilities` | 根据执行结果更新能力权重 |
| 回滚权重更新 | POST | `/api/v1/evo/evolution-events/{id}/revert` | 回滚单个权重更新 |
| 查询进化历史 | GET | `/api/v1/evo/evolution-history` | 获取 Agent 进化历史 |

> **Sprint 104 变更**: 原 `/api/v1/evo/patterns` 系列接口迁移至 `/api/v1/evo/genes`，原 `/api/v1/evo/weight-updates` 迁移至 `/api/v1/evo/evolution-events`。新增 `/api/v1/evo/capsules` 端点。

---

## 三、接口详情

### 3.1 提取 Gene

```
POST /api/v1/evo/genes/extract
Content-Type: application/json

Request Body:
{
  "agent_id": "agent-xxx",
  "task_id": "task-001",
  "success": true,
  "outcome_summary": "成功修复了 Pagination 组件的分页逻辑",
  "confidence": 0.88
}

Response 200:
{
  "type": "gene",
  "id": "gene-repair-0001",
  "category": "repair",
  "signals_match": ["timeout", "connection_error"],
  "strategy": [
    {"action": "enable_exponential_backoff", "value": true}
  ],
  "epigenetic_marks": [
    {"mark": "confidence", "value": 0.88}
  ],
  "created_at": "2026-06-01T14:00:00"
}
```

### 3.2 查询 Gene 列表

```
GET /api/v1/evo/genes
Query Parameters:
  - category: string（可选：capability/pattern/anti_pattern/sequence/condition/constraint）
  - page: int（可选，默认1）
  - page_size: int（可选，默认20）

Response 200:
{
  "items": [
    {
      "type": "gene",
      "id": "gene-capability-0001",
      "category": "capability",
      "signals_match": ["task_type:data_analysis"],
      "strategy": [
        {"action": "recommend_capabilities", "value": ["sql", "python"]}
      ],
      "epigenetic_marks": [
        {"mark": "confidence", "value": 0.85},
        {"mark": "support_count", "value": 15}
      ],
      "created_at": "2026-06-01T14:00:00"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### 3.3 查询 Gene 详情

```
GET /api/v1/evo/genes/{gene_id}

Response 200:
{
  "type": "gene",
  "schema_version": "1.0",
  "id": "gene-retry-001",
  "category": "repair",
  "signals_match": ["timeout", "connection_error"],
  "preconditions": ["task_failed", "retry_allowed"],
  "strategy": [
    {"action": "set_timeout", "value": 30},
    {"action": "enable_exponential_backoff", "value": true}
  ],
  "constraints": {
    "max_files": 10,
    "max_lines": 5000,
    "forbidden_paths": ["src/core/"]
  },
  "validation": ["npm test", "npm lint"],
  "epigenetic_marks": [
    {"mark": "platform", "value": "windows"},
    {"mark": "score", "value": 0.92}
  ],
  "created_at": "2026-06-01T14:00:00",
  "updated_at": "2026-06-01T14:00:00"
}
```

### 3.4 触发技能提炼

```
POST /api/v1/evo/distill
Content-Type: application/json

Request Body:
{
  "agent_id": "agent-xxx",
  "lookback_days": 30,
  "min_success_rate": 0.70
}

Response 200:
{
  "job_id": "distill-001",
  "status": "queued",
  "estimated_duration_seconds": 300,
  "message": "技能提炼任务已排队，预计耗时5分钟"
}

Response 200 (无需提炼):
{
  "job_id": null,
  "status": "skipped",
  "reason": "成功案例不足（需要10个，当前5个）"
}
```

### 3.5 进化能力

```
POST /api/v1/evo/evolve-capabilities
Content-Type: application/json

Request Body:
{
  "agent_id": "agent-xxx",
  "task_id": "task-001",
  "result": "success",
  "execution_time_ms": 45000,
  "signals": ["timeout_recovered", "retry_success"]
}

Response 200:
{
  "agent_id": "agent-xxx",
  "evolution_id": "evo-001",
  "capability_delta": {
    "retry_strategy": 0.05,
    "timeout_handling": 0.03
  },
  "mutation_triggered": true,
  "mutation_type": "optimize",
  "evolution_at": 1716800000
}
```

### 3.6 查询进化历史

```
GET /api/v1/evo/evolution-history
Query Parameters:
  - agent_id: string（可选）
  - days: int（可选，默认30）

Response 200:
{
  "agent_id": "agent-xxx",
  "history": [
    {
      "evolution_id": "evo-001",
      "mutation_type": "optimize",
      "capability_delta": {"retry_strategy": 0.05},
      "outcome": "success",
      "evolution_at": 1716800000
    }
  ],
  "total": 45
}
```

### 3.7 固化能力变更

```
POST /api/v1/evo/solidify
Content-Type: application/json

Request Body:
{
  "evolution_id": "evo-001",
  "auto_publish": false
}

Response 200:
{
  "solidify_id": "solidify-001",
  "status": "success",
  "files_changed": 3,
  "lines_changed": 45,
  "validation_passed": true,
  "validated_at": 1716800100
}

Response 200 (需要人工确认):
{
  "solidify_id": "solidify-002",
  "status": "pending_review",
  "reason": "变更涉及核心模块，需要人工确认",
  "files_impacted": ["src/core/task_runner.py"],
  "can_auto_apply": false
}
```

### 3.8 查询 Capsule 列表

```
GET /api/v1/evo/capsules
Query Parameters:
  - status: string（可选：draft/validated/solidified/deprecated）
  - gene_id: string（可选，按 Gene 筛选）
  - page: int（可选，默认1）

Response 200:
{
  "items": [
    {
      "type": "capsule",
      "schema_version": "1.0",
      "id": "capsule-20260601-001",
      "gene_id": "gene-capability-0001",
      "summary": "数据分析任务中 SQL+Python 能力组合成功率 92%",
      "confidence": 0.92,
      "outcome": {"status": "success", "score": 0.92},
      "success_streak": 5,
      "created_at": "2026-06-01T14:00:00"
    }
  ],
  "total": 28,
  "page": 1
}
```

### 3.9 查询 Capsule 详情

```
GET /api/v1/evo/capsules/{capsule_id}

Response 200:
{
  "type": "capsule",
  "schema_version": "1.0",
  "id": "capsule-20260601-001",
  "gene_id": "gene-capability-0001",
  "summary": "数据分析任务中 SQL+Python 能力组合成功率 92%",
  "confidence": 0.92,
  "blast_radius": {"files_changed": 0, "lines_changed": 0},
  "outcome": {"status": "success", "score": 0.92},
  "success_streak": 5,
  "a2a": {"source": "local", "ready_for_hub": false},
  "created_at": "2026-06-01T14:00:00"
}
```

### 3.10 提升 Capsule 状态

```
PUT /api/v1/evo/capsules/{capsule_id}/promote
Content-Type: application/json

Request Body:
{
  "status": "solidified"
}

Response 200:
{
  "capsule_id": "capsule-20260601-001",
  "old_status": "validated",
  "new_status": "solidified",
  "updated_at": "2026-06-01T14:30:00"
}
```

### 3.11 查询进化事件列表

```
GET /api/v1/evo/evolution-events
Query Parameters:
  - agent_id: string（可选）
  - intent: string（可选：repair/optimize/innovation）
  - page: int（可选，默认1）

Response 200:
{
  "items": [
    {
      "type": "evolution_event",
      "schema_version": "1.0",
      "id": "event-20260601-001",
      "intent": "optimize",
      "genes_used": ["gene-capability-0001"],
      "capsule_id": "capsule-20260601-001",
      "outcome": {"status": "applied", "score": 0.92},
      "created_at": "2026-06-01T14:00:00"
    }
  ],
  "total": 15,
  "page": 1
}
```

### 3.12 回滚权重更新

```
POST /api/v1/evo/evolution-events/{event_id}/revert

Response 200:
{
  "event_id": "event-20260601-001",
  "status": "reverted",
  "reverted_at": "2026-06-01T15:00:00",
  "note": "权重已恢复为更新前的值"
}
```

---

### 3.13 广播经验

```
POST /api/v1/a2a/broadcast
Content-Type: application/json

Request Body:
{
  "sender_id": "agent-xxx",
  "recipient_ids": ["agent-yyy", "agent-zzz"],
  "type": "gene_share",
  "payload": {
    "gene_id": "gene-retry-001",
    "confidence": 0.88,
    "success_streak": 5
  },
  "message": "这是一个重试策略优化，5次连续成功"
}

Response 200:
{
  "broadcast_id": "bc-001",
  "recipients_delivered": 2,
  "delivered_to": ["agent-yyy", "agent-zzz"],
  "broadcast_at": 1716800000
}
```

### 3.14 查询消息

```
GET /api/v1/a2a/messages
Query Parameters:
  - agent_id: string（可选，筛选接收方）
  - type: string（可选：gene_share/belief_update/signal_alert）
  - page: int（可选，默认1）

Response 200:
{
  "items": [
    {
      "message_id": "msg-001",
      "sender_id": "agent-xxx",
      "recipient_ids": ["agent-yyy"],
      "type": "gene_share",
      "payload": {"gene_id": "gene-retry-001"},
      "read": false,
      "received_at": 1716800000
    }
  ],
  "total": 15,
  "unread_count": 3
}
```

### 3.15 更新信念

```
POST /api/v1/evo/update-beliefs
Content-Type: application/json

Request Body:
{
  "agent_id": "agent-xxx",
  "beliefs": {
    "retry_strategy": {
      "confidence": 0.92,
      "last_updated": 1716800000,
      "evidence_count": 45
    },
    "timeout_handling": {
      "confidence": 0.78,
      "last_updated": 1716799000,
      "evidence_count": 12
    }
  }
}

Response 200:
{
  "agent_id": "agent-xxx",
  "updated_count": 2,
  "updated_at": 1716800000
}
```

### 3.16 查询信念

```
GET /api/v1/evo/beliefs
Query Parameters:
  - agent_id: string（可选）

Response 200:
{
  "agent_id": "agent-xxx",
  "beliefs": {
    "retry_strategy": {
      "confidence": 0.92,
      "last_updated": 1716800000,
      "evidence_count": 45,
      "status": "stable"
    },
    "timeout_handling": {
      "confidence": 0.78,
      "last_updated": 1716799000,
      "evidence_count": 12,
      "status": "evolving"
    }
  },
  "overall_confidence": 0.85
}
```

### 3.17 提交 Hub 审核

```
POST /api/v1/evo/submit-hub
Content-Type: application/json

Request Body:
{
  "gene_id": "gene-retry-001",
  "agent_id": "agent-xxx",
  "quality_score": 0.88
}

Response 200:
{
  "submission_id": "sub-001",
  "hub_asset_id": "hub-asset-001",
  "status": "pending_review",
  "submitted_at": 1716800000
}

Response 200 (不满足发布条件):
{
  "submission_id": null,
  "status": "rejected",
  "reason": "success_streak 不足（需要 >= 2，当前 1）",
  "required": {"success_streak": 2},
  "actual": {"success_streak": 1}
}
```

---

## 四、GEP 协议数据格式

### 4.1 Gene 核心字段

```json
{
  "type": "gene",
  "schema_version": "1.0",
  "id": "gene-retry-001",
  "category": "repair",
  "signals_match": ["timeout", "connection_error"],
  "preconditions": ["task_failed", "retry_allowed"],
  "strategy": [
    {"action": "set_timeout", "value": 30},
    {"action": "enable_exponential_backoff", "value": true}
  ],
  "constraints": {
    "max_files": 10,
    "max_lines": 5000,
    "forbidden_paths": ["src/core/"]
  },
  "validation": ["npm test", "npm lint"],
  "epigenetic_marks": [
    {"mark": "platform", "value": "windows"},
    {"mark": "score", "value": 0.92}
  ]
}
```

### 4.2 Capsule 核心字段

```json
{
  "type": "capsule",
  "schema_version": "1.0",
  "id": "capsule-20260601-001",
  "trigger": ["timeout", "connection_error"],
  "gene_id": "gene-retry-001",
  "summary": "成功实施指数退避重试策略",
  "confidence": 0.92,
  "blast_radius": {"files_changed": 0, "lines_changed": 0},
  "outcome": {"status": "success", "score": 0.88},
  "success_streak": 5,
  "a2a": {"source": "local", "ready_for_hub": false}
}
```

### 4.3 EvolutionEvent 核心字段（新增）

```json
{
  "type": "evolution_event",
  "schema_version": "1.0",
  "id": "event-20260601-001",
  "parent_id": null,
  "intent": "optimize",
  "signals": ["pattern_solidified"],
  "genes_used": ["gene-capability-0001"],
  "capsule_id": "capsule-20260601-001",
  "outcome": {"status": "applied", "score": 0.92},
  "env_fingerprint": {"platform": "windows", "architecture": "x64"},
  "meta": {"weight_adjustments": {"sql": 0.1, "python": 0.1}}
}
```

### 4.4 DB 存储表（新增）

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| **genes** | 存储提取的基因 | id, category, signals_match, strategy, constraints, epigenetic_marks |
| **capsules** | 存储固化的记忆体 | id, gene_id, summary, confidence, outcome, success_streak |
| **evolution_events** | 存储进化事件 | id, parent_id, intent, genes_used, capsule_id, outcome |

> Sprint 104 新建 3 张表，迁移脚本 `038_gep_tables.sql`

---

## 五、错误码定义

| HTTP 状态码 | 错误码 | 说明 |
|------------|--------|------|
| 400 | `insufficient_cases` | 成功案例不足，无法提炼 |
| 400 | `invalid_gene_format` | Gene 格式错误 |
| 404 | `pattern_not_found` | 模式不存在 |
| 404 | `agent_not_found` | Agent 不存在 |
| 409 | `already_submitted` | 已提交过审核 |
| 422 | `solidify_blocked` | 固化被安全规则拦截 |

---

*文档结束*
