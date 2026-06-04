# Sprint 76 任务派发清单

> 基于 `docs/sprints/sprint-76-exploration-optimization.md`
> 日期：2026-05-12

---

## Task 76a-1：自动捕获逻辑（后端核心）

**做什么**：任务完成时自动收集 result_summary，写入 solutions 表，必须填 project_ids 和 task_ids

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `auto_capture_solution()` 函数
- `packages/server/src/reins/scheduler/project_executor.py` — 在任务完成收集点注入调用
- `packages/server/src/reins/models/solution.py` — 确认 ORM 模型字段完整

**依赖关系**：depends_on=[]

## Done Criteria
- [ ] Python 编译通过（`python -m py_compile` 0 errors）
- [ ] 新增 `auto_capture_solution()` 函数，签名正确
- [ ] `project_executor.py` 中任务 done 时调用该函数
- [ ] DB 验证：`SELECT project_ids, task_ids FROM solutions` 返回非 null 值
- [ ] 业务验证：完成一个任务 → 方案表自动增加一条记录

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile 0 errors"},
  {"type": "data", "name": "DB数据验证", "desc": "solutions 表 project_ids 和 task_ids 非 null、非空数组", "query": "SELECT project_ids, task_ids FROM solutions WHERE goal_id='test-explore-goal-001'"},
  {"type": "custom", "name": "自动捕获验证", "desc": "跑一次任务完成流程，方案表自动增加记录", "script": "完成一个 test 目标下的任务，检查 solutions 表是否有新记录"}
]}
```

---

## Task 76a-2：方案命名规范化

**做什么**：自动捕获时从任务结果中提取方案名称，而不是用 "方案-1" 这种占位名

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — `auto_capture_solution()` 中的命名逻辑

**依赖关系**：depends_on=["task-76a-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 方案名称格式：`{方案类型}-{方案特点}`（如 "方案A-快速修桥"）
- [ ] DB 验证：solutions.name 字段不是占位名

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "方案名称验证", "desc": "solutions.name 不是 '方案-1' 这种占位名", "query": "SELECT name FROM solutions LIMIT 5"}
]}
```

---

## Task 76b-1：比较引擎（后端）

**做什么**：多方案多维度加权评分，自动更新 score 和 status

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `compare_solutions()` 函数
- `packages/server/src/reins/scheduler/optimization_loop.py` — 集成比较引擎

**依赖关系**：depends_on=["task-76a-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] `compare_solutions()` 函数实现，接受 goal_id 和 new_solution_id
- [ ] 评分逻辑：多维度加权（工期 35% + 成本 35% + 安全系数 30%）
- [ ] DB 验证：solutions.score 非 null，status 自动更新
- [ ] API 验证：`GET /api/v1/solutions/compare?goal_id=xxx` 返回正确结构

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "api", "name": "比较 API", "endpoint": "http://127.0.0.1:8095/api/v1/solutions/compare?goal_id=test-explore-goal-001", "desc": "返回200+包含solutions数组，每个有score字段"},
  {"type": "data", "name": "评分数据验证", "desc": "solutions.score 非 null，status 自动标记（compliant/non_compliant/rejected）", "query": "SELECT id, name, score, status FROM solutions"}
]}
```

---

## Task 76b-2：收敛/进度判断逻辑

**做什么**：探索模式判断是否该选方案了，优化模式判断是否在螺旋推进

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `check_convergence()` 函数
- `packages/server/src/reins/api/goals_exploration.py` — 迭代回路中调用

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 探索模式：改进 < 5% → 提示用户确认
- [ ] 探索模式：改进 < 1% → 自动标记收敛
- [ ] 优化模式：score 持续上升且 >= 90 → 目标达成
- [ ] 优化模式：改进 < 1% → 提示"进入瓶颈，是否调整方向"

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "custom", "name": "收敛判断验证", "desc": "造 3 个 score 接近的方案，验证收敛判断返回 converged=True"}
]}
```

---

## Task 76c-1：约束自动调整

**做什么**：每轮结束后自动收紧约束（工期×0.9、成本×0.9、其他×0.95）

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `adjust_constraints_for_next_round()` 函数
- `packages/server/src/reins/api/goals_exploration.py` — iterate 端点调用

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] DB 验证：点击"下一轮"后，iteration_constraints 表新增记录，constraints JSON 中数值已收紧
- [ ] 任务派发时，新任务的 description 包含约束描述

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "约束数据验证", "desc": "iteration_constraints 表新增 round=N 记录，constraints 中数值已收紧", "query": "SELECT round, constraints FROM iteration_constraints ORDER BY round DESC LIMIT 3"}
]}
```

---

## Task 76c-2：迭代回路完整串联

**做什么**：把 自动捕获 → 比较 → 收敛判断 → 约束调整 串成完整回路

**文件/位置**：
- `packages/server/src/reins/api/goals_exploration.py` — `trigger_iteration()` 完整实现
- `packages/server/src/reins/scheduler/project_executor.py` — 任务 done 触发回路

**依赖关系**：depends_on=["task-76a-1", "task-76b-1", "task-76b-2", "task-76c-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 业务闭环验证：完成一轮任务 → 自动捕获方案 → 比较评分 → 判断收敛 → 点击"下一轮" → 新约束注入 → 新任务派发
- [ ] DB 验证：solutions 表每轮有记录，task_ids 不同，iteration_constraints 有记录

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "custom", "name": "业务闭环验证", "desc": "跑一次完整迭代：完成任务 → 方案自动生成 → 有评分 → 点下一轮 → 新任务带约束", "script": "对 test-explore-goal-001 跑一轮完整迭代"}
]}
```

---

## Task 76d-1：前端方案详情面板

**做什么**：方案列表页点击方案 → 展开详情，显示关联的工程和任务列表

**文件/位置**：
- `packages/ui/src/pages/SolutionList.tsx` — 方案详情展开面板
- `packages/ui/src/services/solutions.ts` — 新增 getDetail API 调用

**依赖关系**：depends_on=["task-76a-1"]

## Done Criteria
- [ ] TS 编译通过（`npx tsc --noEmit` 0 errors）
- [ ] 页面验证：点击方案名 → 展开面板
- [ ] 面板内容：完整参数表 + 关联工程列表（可点击跳转）+ 关联任务列表（含执行结果摘要）
- [ ] 数据验证：关联工程/任务的 ID 能正确从 project_ids/task_ids 解析

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "page", "name": "方案详情页", "url": "http://localhost:5173/goals/test-explore-goal-001/solutions", "desc": "点击方案名能看到关联的工程列表和任务列表，不是空数据"},
  {"type": "data", "name": "关联数据验证", "desc": "方案详情中的工程/任务 ID 与 DB 中 project_ids/task_ids 一致", "query": "SELECT project_ids, task_ids FROM solutions LIMIT 1"}
]}
```

---

## Task 76d-2：前端收敛趋势图（优化模式）

**做什么**：优化模式下显示收敛趋势图（轮次 vs 评分折线图）+ 参数变化表

**文件/位置**：
- `packages/ui/src/pages/SolutionCenter.tsx` — 趋势图组件
- `packages/ui/src/services/solutions.ts` — trend API 调用

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] TS 编译通过
- [ ] 页面验证：趋势图正确显示，横轴=轮次，纵轴=评分
- [ ] 参数变化表显示每轮参数对比

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "page", "name": "趋势图页面", "url": "http://localhost:5173/solutions", "desc": "趋势图有数据，不是空图"}
]}
```

---

## Task 76e-1：端到端闭环验证

**做什么**：用 test-explore-goal-001 跑一次完整的探索→优化流程，验证数据全链路

**文件/位置**：
- 无需改代码，纯验证
- 验证脚本：`scripts/verify_sprint76_e2e.py`

**依赖关系**：depends_on=["task-76a-1", "task-76a-2", "task-76b-1", "task-76b-2", "task-76c-1", "task-76c-2", "task-76d-1", "task-76d-2"]

## Done Criteria
- [ ] 清理 test-explore-goal-001 的旧数据
- [ ] 目标设为 exploration 模式
- [ ] 手动触发第一轮任务完成
- [ ] 验证：方案自动生成，task_ids/project_ids 非 null
- [ ] 验证：比较引擎自动评分
- [ ] 点击"下一轮" → 新任务带约束
- [ ] 第二轮完成 → 新方案，不同参数
- [ ] 切换 optimization 模式 → 继续推进
- [ ] 页面验证：方案详情能看到关联任务/工程

## Acceptance Criteria
```json
{"criteria": [
  {"type": "custom", "name": "端到端验证", "desc": "完整跑通探索→优化流程，7项验证全部通过", "script": "scripts/verify_sprint76_e2e.py"}
]}
```

---

## 任务依赖图

```
76a-1: 自动捕获逻辑（核心）
  ├──→ 76a-2: 方案命名
  ├──→ 76b-1: 比较引擎
  │      ├──→ 76b-2: 收敛判断
  │      └──→ 76c-1: 约束调整
  │             └──→ 76c-2: 迭代回路串联
  └──→ 76d-1: 方案详情面板
         └──→ 76c-2 + 76d-1 + 76d-2 → 76e-1: E2E 验证
```

## 执行顺序

**Phase 1**（并行）：76a-1
**Phase 2**（并行）：76a-2, 76b-1, 76d-1
**Phase 3**（并行）：76b-2, 76c-1, 76d-2
**Phase 4**：76c-2
**Phase 5**：76e-1
