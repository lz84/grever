---
name: genesis
description: 将复杂目标拆解为可执行的项目树和任务树，自动生成 DAG 依赖关系。支持 LLM 智能分解和模式匹配两种模式。
tags: [coordination, decomposition, dag, planning, nexus]
---

# Genesis (生)

目标分解引擎 — 将复杂目标拆解为可执行的项目树/任务树，自动生成 DAG 依赖。

## 何时激活

- 用户需要将目标分解为子任务
- 创建新目标时需要自动生成工作流
- 需要分析任务依赖和并行关系
- 需要估算工作量和时间线

## 配置

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `NEXUS_SERVER_URL` | 否 | `http://localhost:8090` | Nexus API 地址 |
| `LLM_API` | 否 | — | LLM API URL（用于智能分解） |
| `LLM_MODEL` | 否 | `qwen3-30b-a3b-fp8` | LLM 模型名 |
| `GRASP_API` | 否 | — | Grasp 认知库 API（用于领域知识注入） |

## 命令

```bash
python skill.py decompose "Build a disaster response system"
python skill.py decompose "goal text" --no-llm --format json -o output.json
python skill.py list
```

## API 接口

### 分解目标

```bash
POST /api/v1/goals/{goal_id}/decompose
{
  "use_llm": true,
  "inject_grasp": true
}
```

### 预览分解

```bash
POST /api/v1/goals/{goal_id}/decompose/preview
```

不写入数据库，只返回分解方案供审核。

## 分解规则

### 标准流程

```
Phase 1: 需求分析 (1 个 Project)
Phase 2: 开发实现 (N 个并行 Project)
Phase 3: 集成测试 (1 个 Project)
Phase 4: 部署上线 (1 个 Project)
```

### 子任务粒度

- 每个任务 1-4 小时工作量
- 标识前置依赖（finish-to-start）
- 标识可并行任务
- 分配优先级 P0/P1/P2

## 与 Grasp 的集成

分解时可注入认知库知识，生成更贴合业务场景的分解方案。

## 与 Reins 的区别

| 功能 | Genesis | Reins |
|------|---------|-------|
| 目标分解 | ✅ | ❌ |
| DAG 生成 | ✅ | ❌ |
| 项目/任务 CRUD | ❌ | ✅ |
| 状态机流转 | ❌ | ✅ |

Genesis 只负责"生"——从目标中生成执行结构。Reins 负责"缰"——对已有结构进行日常管理。
