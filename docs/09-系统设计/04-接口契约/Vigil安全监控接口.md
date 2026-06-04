# Vigil 安全监控接口

**版本**: v2.0
**作者**: 刚子
**日期**: 2026-05-27
**状态**: 草稿
**关联需求**: Nexus 安全领域
**变更记录**:
- v1.0 2026-05-27 刚子 初始版本
- v2.0 2026-06-02 小二 补充告警管理 CRUD + 安全告警/审计端点（5 端点）

---

## 一、概述

### 1.1 接口范围

本文档定义 Vigil 安全监控相关的所有 API 接口，覆盖信任评估、访问控制、审计日志、告警管理和系统健康五大模块。

### 1.2 Vigil 四层结构

| 层 | 职责 | 核心能力 |
|---|------|---------|
| **外审层** | 对外安全 | RBAC 权限管理、外部访问控制、第三方鉴权 |
| **内审层** | 对内安全 | 行为审计、异常检测、信任评估体系 |
| **日志管理层** | 日志收集/存储/查询/归档 | ELK Stack + 时序数据库 |
| **告警管理层** | 威胁/合规/性能告警 | 规则引擎 + 通知系统 |

---

## 二、接口清单总表

### 2.1 信任评估

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取信任评分 | GET | `/api/v1/vigil/trust/agents/{agent_id}` | 获取 Agent 三维信任评分 |
| 重新评估 | POST | `/api/v1/vigil/trust/agents/{agent_id}/reassess` | 手动触发信任重新评估 |
| 查询评分历史 | GET | `/api/v1/vigil/trust/agents/{agent_id}/history` | 获取 Agent 评分历史 |
| 查询降级告警 | GET | `/api/v1/vigil/trust/alerts/downgrade` | 获取信任降级事件 |

### 2.2 访问控制

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建角色 | POST | `/api/v1/vigil/roles` | 创建 RBAC 角色 |
| 查询角色列表 | GET | `/api/v1/vigil/roles` | 获取角色列表 |
| 查询角色详情 | GET | `/api/v1/vigil/roles/{role_id}` | 获取单个角色详情 |
| 更新角色 | PUT | `/api/v1/vigil/roles/{role_id}` | 更新角色权限 |
| 删除角色 | DELETE | `/api/v1/vigil/roles/{role_id}` | 删除角色 |
| 绑定角色 | POST | `/api/v1/vigil/roles/{role_id}/assign` | 为 Agent 绑定角色 |
| 查询权限 | GET | `/api/v1/vigil/permissions` | 获取所有可用权限列表 |

### 2.3 审计日志

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询审计日志 | GET | `/api/v1/audit/logs` | 审计日志列表 |
| 导出审计日志 | GET | `/api/v1/audit/logs/export` | 导出 CSV 格式 |
| 记录操作日志 | POST | `/api/v1/audit/logs` | 记录操作日志 |

### 2.4 告警管理

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询告警列表 | GET | `/api/v1/alerts` | 获取告警列表 |
| 获取告警详情 | GET | `/api/v1/alerts/{alert_id}` | 获取单个告警详情 |
| 创建告警 | POST | `/api/v1/alerts` | 创建新告警 |
| 更新告警状态 | PATCH | `/api/v1/alerts/{alert_id}` | 处理告警（确认/解决） |
| 删除告警 | DELETE | `/api/v1/alerts/{alert_id}` | 删除告警 |
| 批量已读 | PATCH | `/api/v1/alerts/mark-read` | 批量标记已读 |
| 安全告警列表 | GET | `/api/v1/security/alerts` | 安全域告警列表 |
| 安全审计日志 | GET | `/api/v1/security/audit/logs` | 安全审计日志 |

### 2.5 系统健康

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 系统健康检查 | GET | `/api/v1/health` | 健康检查 |
| 系统指标 | GET | `/api/v1/system/metrics` | 获取系统指标 |

---

## 三、接口详情

### 3.1 获取信任评分

```
GET /api/v1/vigil/trust/agents/{agent_id}

Response 200:
{
  "agent_id": "agent-xxx",
  "overall_score": 0.87,
  "trust_level": 4,
  "dimensions": {
    "capability": {
      "score": 0.90,
      "breakdown": {
        "task_completion_rate": 0.95,
        "quality_score": 0.88,
        "complexity_adaptation": 0.85
      }
    },
    "reliability": {
      "score": 0.85,
      "breakdown": {
        "stability": 0.92,
        "exception_rate": 0.05,
        "response_time": 0.78,
        "recovery_ability": 0.88
      }
    },
    "security": {
      "score": 0.86,
      "breakdown": {
        "privilege_escalation_count": 0,
        "data_compliance": 0.95,
        "security_incidents": 0,
        "audit_pass_rate": 0.98
      }
    }
  },
  "last_reassessed_at": 1716800000,
  "next_scheduled_reassess": 1716886400
}
```

### 3.2 重新评估

```
POST /api/v1/vigil/trust/agents/{agent_id}/reassess
Content-Type: application/json

Request Body:
{
  "reason": "人工重新评估",
  "lookback_days": 30
}

Response 200:
{
  "agent_id": "agent-xxx",
  "overall_score": 0.89,
  "previous_score": 0.87,
  "delta": 0.02,
  "trust_level": 4,
  "reassessed_at": 1716800100
}
```

### 3.3 查询评分历史

```
GET /api/v1/vigil/trust/agents/{agent_id}/history
Query Parameters:
  - days: int（可选，默认30）

Response 200:
{
  "agent_id": "agent-xxx",
  "history": [
    {
      "overall_score": 0.87,
      "trust_level": 4,
      "dimensions": {...},
      "reassessed_at": 1716800000
    },
    {
      "overall_score": 0.85,
      "trust_level": 3,
      "dimensions": {...},
      "reassessed_at": 1716713600
    }
  ],
  "total": 60
}
```

### 3.4 查询降级告警

```
GET /api/v1/vigil/trust/alerts/downgrade

Response 200:
{
  "items": [
    {
      "alert_id": "alert-001",
      "type": "trust_downgrade",
      "severity": "medium",
      "agent_id": "agent-xxx",
      "from_level": 4,
      "to_level": 3,
      "reason": "连续3次验证失败",
      "created_at": 1716800000,
      "status": "active"
    }
  ],
  "total": 5
}
```

### 3.5 创建角色

```
POST /api/v1/vigil/roles
Content-Type: application/json

Request Body:
{
  "name": "化工安全审计员",
  "description": "具有化工领域安全审计权限的角色",
  "permissions": [
    "vigil:read",
    "vigil:audit:read",
    "vigil:alert:acknowledge",
    "chemical:safety:read"
  ]
}

Response 201:
{
  "role_id": "role-001",
  "name": "化工安全审计员",
  "permissions": [...],
  "created_at": 1716800000
}
```

### 3.6 查询审计日志

```
GET /api/v1/audit/logs
Query Parameters:
  - agent_id: string（可选）
  - action: string（可选）
  - start_date: string（可选，ISO8601）
  - end_date: string（可选，ISO8601）
  - page: int（可选，默认1）
  - page_size: int（可选，默认50）

Response 200:
{
  "items": [
    {
      "id": "log-001",
      "agent_id": "agent-xxx",
      "action": "task_complete",
      "resource_type": "task",
      "resource_id": "task-001",
      "result": "success",
      "ip_address": "192.168.1.100",
      "timestamp": 1716800000
    }
  ],
  "total": 1234,
  "page": 1,
  "page_size": 50
}
```

### 3.7 导出审计日志

```
GET /api/v1/audit/logs/export
Query Parameters:
  - format: string（可选：csv，默认 csv）
  - start_date: string（必填）
  - end_date: string（必填）

Response 200:
Content-Type: text/csv
Content-Disposition: attachment; filename="audit_logs_2026-05-01_2026-05-27.csv"

timestamp,agent_id,action,resource_type,resource_id,result
1716800000,agent-xxx,task_complete,task,task-001,success
1716800100,agent-yyy,file_write,file,/path/to/file.py,success
```

### 3.8 查询告警列表

```
GET /api/v1/alerts
Query Parameters:
  - status: string（可选：active/resolved/acknowledged）
  - severity: string（可选：critical/high/medium/low）
  - page: int（可选，默认1）

Response 200:
{
  "items": [
    {
      "alert_id": "alert-001",
      "type": "trust_downgrade",
      "severity": "medium",
      "message": "Agent guzi 信任评分从 0.90 降至 0.75",
      "status": "active",
      "created_at": 1716800000
    }
  ],
  "total": 12,
  "unread_count": 3
}
```

### 3.9 更新告警状态

```
PATCH /api/v1/alerts/{alert_id}
Content-Type: application/json

Request Body:
{
  "status": "acknowledged",
  "note": "已确认，人工调查中"
}

Response 200:
{
  "alert_id": "alert-001",
  "status": "acknowledged",
  "updated_at": 1716800100
}
```

---

## 四、三维信任评估模型

### 4.1 评分权重

| 维度 | 权重 | 说明 |
|------|------|------|
| 能力 (Capability) | 40% | 任务完成率(50%) + 质量分(30%) + 复杂度适应(20%) |
| 可靠性 (Reliability) | 30% | 稳定性(40%) + 异常率(30%) + 响应时间(20%) + 恢复能力(10%) |
| 安全 (Security) | 30% | 越权次数(40%) + 脱敏合规(30%) + 安全事件(20%) + 审计通过率(10%) |

### 4.2 信任等级

| 等级 | 分值范围 | 说明 |
|------|---------|------|
| 5 | 0.90 - 1.00 | 高度可信，可执行敏感操作 |
| 4 | 0.75 - 0.89 | 正常可信，可执行常规操作 |
| 3 | 0.60 - 0.74 | 轻度存疑，需要确认 |
| 2 | 0.40 - 0.59 | 显著存疑，需要额外验证 |
| 1 | 0.00 - 0.39 | 不可信，限制操作 |

---

## 五、错误码定义

| HTTP 状态码 | 错误码 | 说明 |
|------------|--------|------|
| 400 | `invalid_trust_score` | 信任评分格式错误 |
| 404 | `agent_not_found` | Agent 不存在 |
| 404 | `role_not_found` | 角色不存在 |
| 404 | `alert_not_found` | 告警不存在 |
| 409 | `role_name_exists` | 角色名称已存在 |
| 500 | `trust_reassess_failed` | 信任重新评估失败 |

---

*文档结束*
