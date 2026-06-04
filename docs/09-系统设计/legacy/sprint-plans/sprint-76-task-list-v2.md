# Sprint 76 任务派发清单 v2（细化版 + 三流合一）

> 基于 `docs/sprints/sprint-76-exploration-optimization.md`
> 日期：2026-05-12
> **验收纪律**：每个任务必须过 **三流**——数据流 ✅ 业务流 ✅ 页面流 ✅

---

## Phase 1：自动捕获（核心基础）

### Task 76a-1：自动捕获核心逻辑

**做什么**：任务 status 变为 done 时，自动收集该轮所有任务的 result_summary，写入 solutions 表

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `auto_capture_solution(goal_id, db)` 函数
- `packages/server/src/reins/scheduler/project_executor.py` — 在 `_collect_completed_tasks()` 完成后注入调用

**依赖关系**：depends_on=[]

## Done Criteria
- [ ] Python 编译通过（0 errors）
- [ ] `auto_capture_solution()` 函数签名：`(goal_id: str, db: Session) -> Solution`
- [ ] 只在 goal.mode ∈ ('exploration', 'optimization') 时触发
- [ ] 从 tasks.result_summary 提取 parameters
- [ ] 收集该轮所有 project_ids 和 task_ids（非 null）
- [ ] 写入 solutions 表，round 自动 +1

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile 对 solutions.py 和 project_executor.py 编译 0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "DB 中 solutions 表 project_ids 和 task_ids 非 null 非空数组", "query": "SELECT id, project_ids, task_ids FROM solutions WHERE goal_id='test-explore-goal-001' ORDER BY created_at DESC LIMIT 3"},
  {"type": "custom", "name": "业务流验证", "desc": "完成一个测试目标下的任务 → 方案表自动增加一条记录，task_ids 包含已完成任务的 ID", "script": "1. 创建 test goal(mode=exploration) → 2. 创建 task → 3. 标记 task done → 4. 查 solutions 表是否有新记录"},
  {"type": "page", "name": "页面流验证", "desc": "方案列表页能看到新方案，点击展开能看到关联的任务 ID", "url": "http://localhost:5173/goals/test-explore-goal-001/solutions"}
]}
```

---

### Task 76a-2：自动捕获 — 多任务场景

**做什么**：确保一个目标下有多个任务时，所有任务都 done 后才触发捕获（不是每完成一个就捕获一次）

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — `auto_capture_solution()` 中的"全部完成"判断逻辑

**依赖关系**：depends_on=["task-76a-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 判断逻辑：`pending_tasks_count == 0` 时才触发
- [ ] 不重复触发：同一轮次不重复创建方案
- [ ] DB 验证：3 个任务都 done 后，solutions 表只有 1 条记录（不是 3 条）

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "3 个任务都 done 后 solutions 表只有 1 条记录（不是每完成一个就创建一条）", "query": "SELECT COUNT(*) FROM solutions WHERE goal_id='test-multi-task-goal'"},
  {"type": "custom", "name": "业务流验证", "desc": "创建 3 个任务 → 完成 2 个（无方案）→ 完成第 3 个（自动生成 1 条方案）", "script": "对 test-multi-task-goal 创建 3 个任务，逐个标记 done，检查 solutions 表记录数"},
  {"type": "page", "name": "页面流验证", "desc": "方案列表只显示 1 条记录，不是 3 条重复的", "url": "http://localhost:5173/goals/test-multi-task-goal/solutions"}
]}
```

---

### Task 76a-3：自动捕获 — 方案去重

**做什么**：相同 goal_id + round + parameters 不重复创建方案（防重复提交）

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — `auto_capture_solution()` 中增加去重检查

**依赖关系**：depends_on=["task-76a-2"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 去重逻辑：检查同 goal_id + round + parameters 是否已存在
- [ ] 如果已存在 → 不创建新记录，直接返回已有方案
- [ ] DB 验证：相同参数提交 2 次，solutions 表只有 1 条

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "相同参数触发 2 次捕获，solutions 表只有 1 条记录", "query": "SELECT COUNT(*) FROM solutions WHERE goal_id='test-explore-goal-001'"},
  {"type": "custom", "name": "业务流验证", "desc": "对同一目标触发 2 次自动捕获，验证不重复创建", "script": "完成同一组任务 2 次，检查 solutions 表记录数不变"},
  {"type": "page", "name": "页面流验证", "desc": "方案列表没有重复行", "url": "http://localhost:5173/goals/test-explore-goal-001/solutions"}
]}
```

---

## Phase 2：比较 + 前端详情（并行）

### Task 76b-1：比较引擎 — 评分计算

**做什么**：多方案多维度加权评分，自动更新 solutions.score 和 solutions.status

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `compare_solutions(goal_id, db)` 函数
  - `calculate_score(params, optimization_target) -> float`
  - `classify_solution(score) -> str`

**依赖关系**：depends_on=["task-76a-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] `compare_solutions()` 遍历目标下所有方案，计算 score
- [ ] 评分公式：工期 35% + 成本 35% + 安全系数 30%，归一化到 0-100
- [ ] status 自动标记：score ≥ 80 → compliant，60-80 → non_compliant，< 60 → rejected
- [ ] 最优方案标记 is_optimal = 1
- [ ] DB 验证：solutions.score 非 null，status 有值

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "solutions.score 非 null，status 有值，is_optimal=1 的方案只有 1 个", "query": "SELECT id, name, score, status, is_optimal FROM solutions WHERE goal_id='test-explore-goal-001'"},
  {"type": "custom", "name": "业务流验证", "desc": "创建 2 个不同参数的方案 → 自动评分 → 高分方案标记 is_optimal=1", "script": "手动创建 2 个方案（参数不同），调用 compare_solutions，检查 score 和 is_optimal"},
  {"type": "page", "name": "页面流验证", "desc": "方案列表页显示评分数字，最优方案有 🏆 标记", "url": "http://localhost:5173/goals/test-explore-goal-001/solutions"}
]}
```

---

### Task 76b-2：比较引擎 — API 端点

**做什么**：暴露比较结果的 API 端点

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — `GET /solutions/compare` 端点实现

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] API 返回结构：`{goal_id, solutions: [{id, name, score, status, parameters}], best: {...}}`
- [ ] curl 验证返回 200 + 正确 JSON

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "api", "name": "数据流验证", "endpoint": "http://127.0.0.1:8095/api/v1/solutions/compare?goal_id=test-explore-goal-001", "desc": "返回200，JSON 包含 solutions 数组，每个有 score/status/parameters 字段"},
  {"type": "custom", "name": "业务流验证", "desc": "API 返回的 solutions 列表与 DB 中 solutions 表记录数一致，best 是 score 最高的", "script": "curl API → 对比 DB 记录数 → 验证 best.score 是最高的"},
  {"type": "page", "name": "页面流验证", "desc": "方案对比中心页面能加载数据，不是空白", "url": "http://localhost:5173/solutions"}
]}
```

---

### Task 76d-1：前端方案详情面板

**做什么**：方案列表页点击方案 → 展开详情，显示完整参数 + 关联工程 + 关联任务

**文件/位置**：
- `packages/ui/src/pages/SolutionList.tsx` — 新增方案详情展开面板
- `packages/ui/src/services/solutions.ts` — 确认 getDetail API 调用

**依赖关系**：depends_on=["task-76a-1"]

## Done Criteria
- [ ] TS 编译通过（`npx tsc --noEmit` 0 errors）
- [ ] 点击方案名 → 展开面板（不是弹窗，是内联展开）
- 面板内容：
  - [ ] 完整参数表（key-value 列表）
  - [ ] 关联工程列表（从 project_ids 查询，显示名称+状态+可点击跳转）
  - [ ] 关联任务列表（从 task_ids 查询，显示名称+执行结果摘要+状态）
  - [ ] 本轮约束条件（从 constraints 解析）
- [ ] 数据验证：ID 能从 project_ids/task_ids JSON 正确解析

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "方案详情中的工程/任务列表，其 ID 与 DB 中 project_ids/task_ids 一致", "query": "SELECT project_ids, task_ids FROM solutions WHERE goal_id='test-explore-goal-001' LIMIT 1"},
  {"type": "custom", "name": "业务流验证", "desc": "点击方案A → 展开面板 → 能看到关联的任务列表，点击任务名能跳转到任务详情", "script": "打开方案列表页 → 点击方案 → 验证展开内容"},
  {"type": "page", "name": "页面流验证", "desc": "展开面板渲染正确，工程列表和任务列表不是空数据，不是 null", "url": "http://localhost:5173/goals/test-explore-goal-001/solutions"}
]}
```

---

## Phase 3：收敛 + 约束调整（并行）

### Task 76b-3：收敛判断逻辑

**做什么**：判断是否该收敛（探索模式）或是否进入瓶颈（优化模式）

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `check_convergence(goal_id, db) -> dict`
- `packages/server/src/reins/api/goals_exploration.py` — iterate 端点调用

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 探索模式：
  - [ ] 改进 < 5% → 返回 requires_human: True
  - [ ] 改进 < 1% → 返回 converged: True
- [ ] 优化模式：
  - [ ] score 持续上升且 >= 90 → done: True
  - [ ] 改进 < 1% → requires_human: True（"进入瓶颈，是否调整方向？"）
- [ ] DB 验证：收敛后 goals.run_status = 'converged'

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "收敛后 goals.run_status = 'converged'，最优方案 is_optimal = 1", "query": "SELECT run_status FROM goals WHERE id='test-explore-goal-001'; SELECT is_optimal FROM solutions WHERE goal_id='test-explore-goal-001'"},
  {"type": "custom", "name": "业务流验证", "desc": "造 3 个 score 接近的方案（92.0, 92.1, 92.2），调用 check_convergence → 返回 converged=True", "script": "手动插入 3 个相近 score 的方案 → 调用 check_convergence → 验证返回"},
  {"type": "page", "name": "页面流验证", "desc": "收敛后迭代控制面板显示'已收敛'状态，下一轮按钮禁用", "url": "http://localhost:5173/goals/test-explore-goal-001"}
]}
```

---

### Task 76c-1：约束自动调整

**做什么**：每轮结束后自动收紧约束（工期×0.9、成本×0.9、安全系数×1.05）

**文件/位置**：
- `packages/server/src/reins/api/solutions.py` — 新增 `adjust_constraints_for_next_round(goal_id, db) -> dict`
- `packages/server/src/reins/api/goals_exploration.py` — `trigger_iteration()` 调用

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 约束调整规则：
  - [ ] 工期/成本类 × 0.9（收紧）
  - [ ] 安全系数类 × 1.05（提高要求）
  - [ ] 其他数值 × 0.95
- [ ] 写入 iteration_constraints 表，round = 上一轮 + 1
- [ ] DB 验证：点击"下一轮"后 constraints 数值已调整

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "iteration_constraints 新增 round=N+1 记录，constraints JSON 中工期×0.9、成本×0.9", "query": "SELECT round, constraints FROM iteration_constraints WHERE goal_id='test-explore-goal-001' ORDER BY round DESC LIMIT 2"},
  {"type": "custom", "name": "业务流验证", "desc": "当前轮约束 {工期:10, 成本:300} → 调用 adjust → 返回 {工期:9.0, 成本:270.0}", "script": "调用 adjust_constraints_for_next_round，验证返回数值正确"},
  {"type": "page", "name": "页面流验证", "desc": "约束历史面板能看到每轮的约束变化", "url": "http://localhost:5173/goals/test-explore-goal-001"}
]}
```

---

### Task 76c-2：约束注入任务描述

**做什么**：新任务派发时，将本轮约束注入到任务描述中

**文件/位置**：
- `packages/server/src/reins/scheduler/project_executor.py` — `_build_task_description()` 注入约束
- `packages/server/src/reins/services/task_dispatcher.py` — 派发时携带约束

**依赖关系**：depends_on=["task-76c-1"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 新任务的 description 包含约束描述："当前约束：工期≤9天，成本≤270万，安全系数≥1.9"
- [ ] DB 验证：tasks.description 包含约束信息

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "新任务的 tasks.description 包含约束关键词（工期、成本、安全系数）", "query": "SELECT id, title, description FROM tasks WHERE goal_id='test-explore-goal-001' ORDER BY created_at DESC LIMIT 3"},
  {"type": "custom", "name": "业务流验证", "desc": "点击'下一轮' → 新任务创建 → description 包含本轮约束", "script": "触发 iterate → 检查新任务的 description 字段"},
  {"type": "page", "name": "页面流验证", "desc": "任务详情页能看到约束描述", "url": "http://localhost:5173/coordination/tasks/{new-task-id}"}
]}
```

---

## Phase 4：迭代回路串联

### Task 76c-3：迭代回路完整串联

**做什么**：把 自动捕获 → 比较 → 收敛判断 → 约束调整 串成完整回路

**文件/位置**：
- `packages/server/src/reins/api/goals_exploration.py` — `trigger_iteration()` 完整实现
- `packages/server/src/reins/scheduler/project_executor.py` — 任务 done 触发回路

**依赖关系**：depends_on=["task-76a-3", "task-76b-3", "task-76c-2"]

## Done Criteria
- [ ] Python 编译通过
- [ ] 完整回路：任务 done → 自动捕获 → 比较评分 → 收敛判断 → 用户点"下一轮" → 约束调整 → 新任务带约束 → 新任务 done → 新一轮捕获
- [ ] DB 验证：
  - [ ] solutions 表每轮有记录
  - [ ] 每轮 task_ids 不同（新任务）
  - [ ] iteration_constraints 每轮有记录

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "2 轮迭代后：solutions 表有 2 条记录（不同 task_ids），iteration_constraints 有 2 条记录（不同 constraints）", "query": "SELECT round, project_ids, task_ids FROM solutions; SELECT round, constraints FROM iteration_constraints"},
  {"type": "custom", "name": "业务流验证", "desc": "跑 2 轮完整迭代：完成任务 → 方案生成 → 比较评分 → 点下一轮 → 新任务带约束 → 完成 → 新方案不同参数", "script": "对 test-explore-goal-001 跑 2 轮迭代，验证每轮数据独立"},
  {"type": "page", "name": "页面流验证", "desc": "方案列表显示 2 个方案（不同参数、不同评分），迭代控制面板显示当前轮次", "url": "http://localhost:5173/goals/test-explore-goal-001/solutions"}
]}
```

---

## Phase 5：前端趋势图

### Task 76d-2：收敛趋势图

**做什么**：优化模式下显示收敛趋势图（轮次 vs 评分折线图）+ 参数变化表

**文件/位置**：
- `packages/ui/src/pages/SolutionCenter.tsx` — 趋势图组件
- `packages/ui/src/services/solutions.ts` — trend API 调用

**依赖关系**：depends_on=["task-76b-1"]

## Done Criteria
- [ ] TS 编译通过（`npx tsc --noEmit` 0 errors）
- [ ] 趋势图：横轴=轮次，纵轴=评分，折线连接各轮 score
- [ ] 参数变化表：每行一个轮次，列=参数名，值=参数值
- [ ] 页面验证：图表有数据，不是空图

## Acceptance Criteria
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "data", "name": "数据流验证", "desc": "trend API 返回的 rounds 和 scores 与 solutions 表一致", "query": "SELECT round, score FROM solutions ORDER BY round"},
  {"type": "custom", "name": "业务流验证", "desc": "有 2 个方案时趋势图显示 2 个点，3 个方案显示 3 个点", "script": "创建多个方案 → 打开趋势图 → 验证点数正确"},
  {"type": "page", "name": "页面流验证", "desc": "趋势图正确渲染，有坐标轴、有数据点、有折线连接，不是空图", "url": "http://localhost:5173/solutions"}
]}
```

---

## Phase 6：E2E 验证

### Task 76e-1：端到端闭环验证

**做什么**：用 test-explore-goal-001 跑一次完整的探索→优化流程，验证数据全链路

**文件/位置**：
- 无需改代码，纯验证
- 验证脚本：`scripts/verify_sprint76_e2e.py`

**依赖关系**：depends_on=["task-76a-1", "task-76a-2", "task-76a-3", "task-76b-1", "task-76b-2", "task-76b-3", "task-76c-1", "task-76c-2", "task-76c-3", "task-76d-1", "task-76d-2"]

## Done Criteria
- [ ] 清理 test-explore-goal-001 旧数据
- [ ] 目标设为 exploration 模式
- [ ] 触发第一轮任务完成
- [ ] ✅ 数据流：方案自动生成，task_ids/project_ids 非 null
- [ ] ✅ 数据流：比较引擎自动评分
- [ ] ✅ 业务流：点击"下一轮" → 新任务带约束
- [ ] ✅ 数据流：第二轮完成 → 新方案，不同参数
- [ ] ✅ 业务流：切换 optimization 模式 → 继续推进
- [ ] ✅ 页面流：方案详情能看到关联任务/工程
- [ ] ✅ 页面流：趋势图有数据

## Acceptance Criteria
```json
{"criteria": [
  {"type": "custom", "name": "数据流验证", "desc": "DB 中 solutions 表 task_ids/project_ids 非 null，score 有值，status 有值，收敛后 run_status=converged", "script": "python scripts/verify_sprint76_e2e.py --check=data"},
  {"type": "custom", "name": "业务流验证", "desc": "完整跑通：探索(2轮) → 选方案 → 优化(1轮) → 收敛", "script": "python scripts/verify_sprint76_e2e.py --check=business"},
  {"type": "custom", "name": "页面流验证", "desc": "方案列表/详情/趋势图/迭代控制面板全部正常渲染，关键数据正确显示", "script": "python scripts/verify_sprint76_e2e.py --check=page"}
]}
```

---

## 任务依赖图

```
Phase 1（串行）
  76a-1: 自动捕获核心
    └──→ 76a-2: 多任务场景
           └──→ 76a-3: 方案去重

Phase 2（76a-1 完成后并行）
  76a-1 ──→ 76b-1: 比较引擎评分
               └──→ 76b-2: 比较 API
  76a-1 ──→ 76d-1: 方案详情面板

Phase 3（76b-1 完成后并行）
  76b-1 ──→ 76b-3: 收敛判断
  76b-1 ──→ 76c-1: 约束调整
               └──→ 76c-2: 约束注入任务描述

Phase 4
  76a-3 + 76b-3 + 76c-2 ──→ 76c-3: 迭代回路串联

Phase 5
  76b-1 ──→ 76d-2: 趋势图

Phase 6
  全部完成 ──→ 76e-1: E2E 验证
```

## 执行计划

| Phase | 任务 | 状态 |
|-------|------|------|
| 1 | 76a-1 → 76a-2 → 76a-3 | 待执行 |
| 2 | 76b-1, 76d-1（并行） | 待执行 |
| 3 | 76b-3, 76c-1→76c-2（并行） | 待执行 |
| 4 | 76c-3 | 待执行 |
| 5 | 76d-2 | 待执行 |
| 6 | 76e-1 | 待执行 |

---

## 三流合一验证标准（固化）

每个任务完成后，必须验证 **三流**：

| 流 | 验证内容 | 方法 |
|---|----------|------|
| **数据流** | DB 数据是否正确 | 查表、查字段、查关联 |
| **业务流** | 业务流程是否跑通 | 真的跑一次，看数据流动 |
| **页面流** | 页面是否正确渲染 | 打开页面，看关键数据 |

**三流缺一 = 任务没完成，不能汇报。**
