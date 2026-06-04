---
name: pulse
description: 智能体注册到 Nexus 平台，心跳保活、在线智能体发现和状态报告。心跳不仅保活，也是任务分发的触发点。
tags: [infrastructure, lifecycle, heartbeat, registration, nexus]
---

# 生命周期

智能体生命周期管理 — 注册、心跳、发现、状态报告。

## 何时激活

- 智能体启动时注册到 Nexus
- 持续发送心跳保活
- 发现其他在线智能体
- 查询自身连接状态

## 命令

```bash
python skill.py connect
python skill.py disconnect
python skill.py heartbeat
python skill.py discover [关键词]
python skill.py status
```

## API 参考

### 注册智能体

```bash
POST {NEXUS_SERVER_URL}/api/v1/智能体s
{
  "智能体_id": "kouzi",
  "name": "扣子",
  "capabilities": ["coding", "testing"],
  "max_load": 5,
  "trigger_mode": "sse"
}
```

### 发送心跳

```bash
POST {NEXUS_SERVER_URL}/api/v1/智能体s/{智能体_id}/heartbeat
{
  "state": "idle",
  "load": 10,
  "current_tasks": 0
}
```

**返回**: 包含 `assigned_tasks` 列表（如果有分配给该智能体的任务）

### 注销智能体

```bash
DELETE {NEXUS_SERVER_URL}/api/v1/智能体s/{智能体_id}
```

## 与其他技能的关系

- **执行引擎**: 依赖生命周期注册和心跳来领取任务
- **统一验证**: 依赖生命周期注册为验证者智能体
- **目标分解**: 不需要生命周期（分解不涉及智能体身份）
