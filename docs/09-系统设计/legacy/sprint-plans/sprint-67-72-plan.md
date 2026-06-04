# Sprint 67-72 详细规划：迭代优化能力

> 基线：`v1.0-waterfall`（Sprint 66 完成）  
> 目标：从"瀑布式任务管理"进化到"迭代优化+方案择优"  
> 设计文档：`docs/evolution/下一阶段进化方向-迭代优化.md`  
> 原则：每个 Sprint = 前端 + 后端 + 集成 + 验证，不按层拆分

---

## Sprint 67：方案库底层（后端基础）

**一句话**：给 Nexus 加上"记住方案"的能力，方案属于目标级

### 后端
- **DB Migration 024**：新增 2 张表
  ```sql
  -- 方案库（目标级）
  CREATE TABLE solutions (
      id TEXT PRIMARY KEY,
      goal_id TEXT REFERENCES goals(id),
      round INTEGER DEFAULT 1,
      name TEXT,
      status TEXT,                         -- optimal / compliant / non_compliant / rejected
      parameters TEXT,                     -- JSON
      dimensions TEXT,                     -- JSON
      score REAL,
      is_optimal BOOLEAN DEFAULT 0,
      project_ids TEXT,                    -- JSON: [本轮涉及的工程ID]
      task_ids TEXT,                       -- JSON: [本轮涉及的任务ID]
      constraints TEXT,                    -- JSON: 本轮约束条件
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  );
  CREATE INDEX idx_solutions_goal ON solutions(goal_id);
  CREATE INDEX idx_solutions_round ON solutions(goal_id, round);

  -- 约束历史
  CREATE TABLE iteration_constraints (
      id TEXT PRIMARY KEY,
      goal_id TEXT REFERENCES goals(id),
      round INTEGER,
      constraints TEXT,                    -- JSON
      reason TEXT,
      created_by TEXT,                     -- 'system' / 'human'
      created_at TIMESTAMP
  );
  CREATE INDEX idx_constraints_goal ON iteration_constraints(goal_id);
  ```

- **DB Migration 025**：goals/projects 表新增探索模式字段
  ```sql
  ALTER TABLE goals ADD COLUMN mode TEXT DEFAULT 'normal';
  ALTER TABLE goals ADD COLUMN optimization_target TEXT;
  ALTER TABLE goals ADD COLUMN convergence_threshold REAL DEFAULT 0.05;
  ALTER TABLE goals ADD COLUMN max_rounds INTEGER DEFAULT 10;
  ALTER TABLE projects ADD COLUMN mode TEXT DEFAULT 'normal';
  ```

- **ORM Model**：`Solution` + `IterationConstraint` 模型
- **API 端点**：
  - `POST /api/v1/solutions` — 手动创建方案（方案参数作为请求体传入）
  - `GET /api/v1/solutions?goal_id=xxx` — 查询某目标下的所有方案
  - `GET /api/v1/solutions/{id}` — 方案详情
  - `PUT /api/v1/solutions/{id}` — 更新方案状态/评分
  - `DELETE /api/v1/solutions/{id}` — 删除方案
  - `POST /api/v1/goals/{id}/mode` — 切换目标/工程的探索模式

### 前端
- **Goal 创建/编辑表单**：新增探索模式选项
  - 模式选择：常规 / 探索
  - 探索模式下显示：优化目标下拉框、收敛阈值输入、最大轮次输入
- **Project 编辑**：新增模式选项（默认继承 goal，可手动覆盖）
- **方案列表页骨架**：`/goals/{id}/solutions` 路由 + 基础布局
- 空状态占位 + 列表占位

### 集成验证
- 创建目标时选择探索模式 → DB 正确写入 mode + optimization_target
- 切换工程模式 → DB 正确覆盖
- curl 创建 2 个方案 → API 返回列表 → 前端能看到 2 条记录

---

## Sprint 68：方案自动捕获 + 方案列表页完整实现

**一句话**：任务完成自动记方案，前端能看方案列表

### 后端
- **自动捕获逻辑**：在任务 done 时注入方案提取
  - 检测：目标 mode == 'exploration' AND 任务状态变为 done
  - 从任务的 `result_summary` 和 `execution_log` 中提取关键参数
  - 调用 `create_solution()` 写入 solutions 表
  - 方案关联 goal_id（目标级），同时记录涉及的 project_ids 和 task_ids
  - 记录本轮约束条件到 iteration_constraints 表
- **方案命名规则**：
  - `方案-{round}-{目标名简写}`

### 前端
- **方案列表页完整实现**（`/goals/{id}/solutions`）：
  - 表格展示：轮次、方案名、状态、核心参数、评分、创建时间
  - 状态标签：✅ 达标（绿色）、❌ 不达标（红色）、🏆 最优（金色）、⛔ 否决（灰色）
  - 点击方案名 → 弹出详情 Modal
- **方案详情 Modal**：
  - 方案完整参数（JSON 展开显示）
  - 关联工程任务列表（点击跳转 ProjectDetail / TaskDetail）
  - 操作按钮：标记为最优、否决、删除

### 集成验证
- 探索模式下完成一个任务 → 自动在方案列表看到新方案
- 手动创建方案 → 列表实时更新
- 常规模式下完成任务 → 不会自动创建方案

---

## Sprint 69：迭代决策回路（核心逻辑）

**一句话**：Nexus 学会"收结果→比较→判断→再派"的循环

### 后端
- **Optimization Loop 编排逻辑**（新增 `optimization_loop.py`）：
  - `OptimizationLoop` 状态机：`idle → comparing → converging → converged`
  - 每次任务 done → 自动触发 `compare_solutions()`（仅当 goal mode == exploration）
- **方案比较引擎**：
  - 输入：当前方案 + 历史所有方案
  - 输出：比较结果（哪个更优、优在哪些维度、改进幅度）
  - 比较逻辑：多维度加权评分（权重可配置）
- **收敛判断规则**：
  - 改进幅度阈值：连续 2 轮改进 < 5% → 准备收敛 → **强制人类确认**
  - 最大迭代轮次：达到 max_rounds → 暂停 → 等待人类决策
  - 达标即收敛：所有核心维度都达标 → 准备收敛
- **API 端点**：
  - `GET /api/v1/solutions/compare?goal_id=xxx` — 获取最新比较结果
  - `POST /api/v1/solutions/{id}/converge` — 手动标记收敛
  - `POST /api/v1/goals/{id}/start-iteration` — 启动迭代回路
  - `GET /api/v1/goals/{id}/iteration-status` — 获取迭代状态

### 前端
- **迭代状态指示器**（GoalDetail 页面顶部新增区域）：
  - 当前迭代轮次：`第 3 轮 / 最大 10 轮`
  - 迭代状态：`进行中` / `已收敛` / `已暂停` / `等待人类确认`
  - 最新比较结果摘要：`方案C vs 方案B：工期↓7%，成本↓5%，安全↑8%`
- **收敛控制按钮**：
  - `继续迭代` → 调整约束，重新派发
  - `宣布收敛` → 标记当前方案为最优
  - `暂停迭代` → 临时停止
  - `换方向` → 重新定义优化目标

### 集成验证
- 连续完成 3 个任务 → 每次自动触发比较 → 第 3 次检测到改进幅度 < 5% → 状态变为 `waiting_human`
- 人类确认"收敛" → 状态变为 converged
- 人类确认"继续" → 触发下一轮

---

## Sprint 70：约束调整 + 迭代控制 UI

**一句话**：Nexus 能根据上一轮结果自动调整约束，前端能控制迭代

### 后端
- **约束模型**：
  - 约束格式：`{"工期": {"max": "6天", "reason": "上一轮7天，优化目标≤6天"}}`
- **约束自动调整逻辑**：
  - 输入：上一轮方案参数 + 优化目标（最短工期/最低成本/综合最优）
  - 输出：新约束条件
  - 策略：
    - 最短工期模式：将上一轮工期 × 0.9 作为新上限
    - 最低成本模式：将上一轮成本 × 0.9 作为新上限
    - 综合最优模式：所有维度各收紧 5%
- **约束注入 Prompt**：
  - 重新派发任务时，将新约束注入到任务描述中
  - 智能体在约束范围内工作
- **API 端点**：
  - `POST /api/v1/goals/{id}/iterate` — 触发下一轮迭代（自动调整约束 + 重新派发）
  - `GET /api/v1/goals/{id}/constraints` — 查看约束历史

### 前端
- **约束历史面板**（GoalDetail 页面新增 Tab）：
  - 每轮约束条件列表（轮次、约束内容、调整原因）
  - 时间线展示：第1轮无约束 → 第2轮工期≤6天 → 第3轮工期≤5.5天
- **迭代控制面板**：
  - 优化目标选择器：最短工期 / 最低成本 / 综合最优
  - 最大迭代轮次输入框（默认 10）
  - 改进幅度阈值输入框（默认 5%）
- **方案对比快速预览**（嵌入 GoalDetail 页面底部）：
  - 最近 2 个方案的 3-4 个核心维度横向对比
  - 绿色箭头表示改善，红色箭头表示恶化

### 集成验证
- 完成方案A（工期7天）→ 点击"继续迭代" → 自动创建新约束（工期≤6.3天）→ 新任务派发带约束描述
- 约束历史面板正确显示每轮调整记录

---

## Sprint 71：方案对比视图（SolutionCenter 页面）

**一句话**：独立的方案对比页面，多维度横向对比 + 收敛趋势图

### 前端
- **SolutionCenter 页面**（`/solutions` 路由）：
  - 目标筛选器（选择要对比的目标）
  - 默认展示该目标下所有方案
- **多维度对比表格**：
  - 横向：方案 A / B / C / ...
  - 纵向：各维度指标（工期、安全系数、成本、风险...）
  - 最优值高亮（绿色背景）
  - 达标值标注 ✅，不达标标注 ❌
  - 最优方案整列金色边框
- **收敛趋势图**：
  - 使用 ECharts 或 recharts
  - 折线图：横轴迭代轮次，纵轴指标值
  - 多条线：工期线、成本线、安全评分线
  - 收敛点标注：在哪一轮收敛的
- **方案详情展开**：
  - 点击任意方案 → 展开侧边抽屉
  - 显示：完整参数、关联工程任务、执行日志、约束条件
  - 操作：标记最优、否决、删除

### 后端
- **对比 API**：
  - `GET /api/v1/solutions/compare/multi?goal_id=xxx` — 返回所有方案的多维度数据（供前端表格使用）
  - 返回格式：`{dimensions: [...], solutions: [{name, parameters, status, score, ...}]}`
- **趋势数据 API**：
  - `GET /api/v1/solutions/trend?goal_id=xxx` — 返回收敛趋势数据（供前端图表使用）
  - 返回格式：`{rounds: [1,2,3], metrics: {工期: [7, 6.5, 6], 成本: [500, 450, 420]}}`

### 集成验证
- 打开 SolutionCenter → 选择目标 → 看到对比表格和趋势图 → 数据与 API 返回一致

---

## Sprint 72：端到端闭环 + 大桥场景演示

**一句话**：用大桥抢修场景跑通完整迭代流程，验证端到端可用性

### 集成工作
- **大桥场景数据准备**：
  - 创建目标："克里米亚大桥战时抢修" → 探索模式，优化目标"综合最优"
  - 创建 4 个工程：战损勘察、方案推演、资源调度、施工管控
  - 工程二（方案推演）保持探索模式，其他 3 个改为常规模式
  - 在目标下跑 3 轮迭代：
    - 第 1 轮：临时钢桁架方案 → 不达标
    - 第 2 轮：局部换梁方案 → 达标
    - 第 3 轮：全段重建方案 → 不可用
- **完整流程验证**：
  1. 定义目标（探索模式）→ LLM 分解 → 生成工程 → 生成任务
  2. 任务派发 → 智能体执行 → 任务完成
  3. 自动捕获方案 → 写入 solutions 表（目标级）
  4. 自动比较 → 判断是否收敛 → 触发人类确认
  5. 不收敛 → 调整约束 → 重新派发 → 下一轮
  6. 收敛 → 人类确认 → 标记最优方案 → 场景沉淀
- **前端全流程验证**：
  - GoalDetail：看到迭代状态、方案列表、收敛控制、约束历史
  - SolutionCenter：看到 3 个方案的对比表格和趋势图
  - 点击方案 → 展开详情 → 查看关联工程任务执行记录

### 验证标准
- [ ] 端到端流程无报错
- [ ] 方案自动捕获准确率 100%
- [ ] 比较逻辑正确识别最优方案
- [ ] 收敛判断在改进 < 5% 时触发人类确认
- [ ] 约束调整自动收紧参数
- [ ] SolutionCenter 对比表格数据正确
- [ ] 趋势图正确显示收敛曲线
- [ ] 强制人类确认节点正常工作

---

## 依赖关系图

```
Sprint 67（DB + API + 探索模式字段）
    ↓
Sprint 68（自动捕获 + 方案列表页）
    ↓
Sprint 69（迭代决策回路 + 比较引擎 + 人类确认节点）
    ↓
Sprint 70（约束调整 + 迭代控制 UI）
    ↓
Sprint 71（SolutionCenter 对比页面）
    ↓
Sprint 72（端到端闭环 + 大桥场景演示）
```

## 与旧计划的差异

| 变更点 | 旧计划 | 新计划 |
|-------|--------|--------|
| 方案归属 | 工程级 | **目标级** |
| 方案列表路由 | `/projects/{id}/solutions` | `/goals/{id}/solutions` |
| 探索模式 | 无明确定义 | **目标/工程两级，可继承可覆盖** |
| 人类确认 | 仅在 dispute 时 | **收敛前强制人类确认节点** |
| 新增表 | solutions 一张 | **solutions + iteration_constraints 两张** |
| 新增字段 | 无 | **goals 新增 4 字段，projects 新增 1 字段** |

---

每个 Sprint 完成后必须通过验收三板斧：
1. ✅ TypeScript 编译 0 errors
2. ✅ API curl 验证通过（200 + 正确 JSON）
3. ✅ 页面能正常渲染（不是白屏）
