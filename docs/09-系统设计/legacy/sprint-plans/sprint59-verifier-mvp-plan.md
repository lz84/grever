# Sprint 59: Verifier Agent MVP — 自动修复循环

> 最小可用版本：Agent 验证 + comment 写入 + 自动修复循环

## 目标

让 Nexus 支持"执行 → 验证 → 不通过自动修复"的正向循环。

## 任务清单

### Phase 1: ResultVerifier 薄分发层（2h）

**Task 1.1**: 改造 `result_verifier.py` 为分发层
- 解析 acceptance_criteria，按 type 分类
- 客观检查（compile/api/file/custom）→ 直接调对应验证逻辑
- 主观检查（llm_review）→ 创建验证任务推给 Nexus Worker
- 汇总结果，写 comment 到 task_comments
- 全部通过 → done；不通过 → review_needed（触发自动修复）
- 文件: `reins/scheduler/result_verifier.py`

**Task 1.2**: comment 写入 `task_comments` 表
- 每次验证后写入结构化 comment
- 格式: author_role="verifier", type="verification_result", content=详细意见
- 文件: `reins/scheduler/result_verifier.py`

### Phase 2: 自动修复循环（1.5h）

**Task 2.1**: 派发回 Executor
- 验证不通过时，自动创建修复任务派发回原 Executor
- 附带最近 verification comment 作为上下文
- 文件: `reins/api/assignment.py` (heartbeat 派发 review_needed 任务)

**Task 2.2**: max_cycles 限制
- verification_cycle >= 3 → 升级为 disputed → 转人工裁决
- 文件: `reins/scheduler/result_verifier.py`

### Phase 3: Worker 集成（1.5h）

**Task 3.1**: Verifier Agent 使用现有 Worker 链路
- 复用 agent_worker.py（已跑通）
- 验证任务通过 Worker 正常派发
- 文件: `scripts/agent_worker.py`（无需改动，已支持）

**Task 3.2**: task-dispatch skill 供 Agent 使用
- Agent 可以通过 REST API 创建验证任务
- 文件: `nexus-skills/task-dispatch/SKILL.md`（已创建骨架）

### Phase 4: E2E 验证（1h）

**Task 4.1**: 端到端测试 — 正向循环
- 创建一个有验收标准的任务
- Executor 报完成 → Verifier 验证通过 → done
- 验证不通过 → review_needed → Executor 修复 → 再次验证 → done

## Sprint 信息

- **Goal**: verifier-agent-e2e
- **Agent**: kouzi（可配置）
- **预计工时**: 6h
