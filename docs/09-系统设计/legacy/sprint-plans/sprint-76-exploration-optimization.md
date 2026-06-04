# Sprint 76：探索模式 & 优化模式 完整规划

> **日期**：2026-05-12
> **根因**：Sprint 68-73 方案与执行链路割裂，task_ids/project_ids 全 null
> **原则**：每个方案必须关联实际执行的任务和工程，能看到完整执行链路

---

## 一、两种模式的本质区别

| 维度 | 探索模式（Exploration） | 优化模式（Optimization） |
|------|------------------------|-------------------------|
| **一句话** | "还有没有别的做法？" | "这个方向怎么走能到终点？" |
| **目标** | 生成多个**不同**的方案供对比 | 对选定方案**螺旋式推进**，分阶段落地实施 |
| **方案关系** | 平行的（A方案修桥、B方案浮桥、C方案渡轮） | 递进的（阶段1勘测 → 阶段2基础 → 阶段3主体 → 阶段4收尾） |
| **每轮做什么** | 换思路、换场景、换工程组合 | 同方向，按计划执行下一阶段任务 |
| **结束条件** | 用户选出一个方案 → 进入优化 | 目标达成 / 预算耗尽 / 所有阶段完成 |
| **用户操作** | 看方案 → 选一个 → 确认进入优化 | 看进度 → 确认阶段成果 → 继续下一阶段 |
| **数据关联** | 每个方案的 task_ids/project_ids **不同** | 每阶段 task_ids/project_ids **不同**（新任务，但同方向） |

---

## 二、探索模式完整数据流

```
1. 用户创建目标，选择 mode = 'exploration'
   goals: { id, title, mode: 'exploration', optimization_target, convergence_threshold, max_rounds }

2. 用户激活目标（或手动启动探索）
   → 目标状态: draft → in_progress

3. Nexus 派发第一轮任务（方案A）
   → 创建 project(s) → 创建 task(s)
   → tasks: { id, goal_id, project_id, title, status: 'todo' }
   → 记录本轮约束到 iteration_constraints: { goal_id, round: 1, constraints: {...} }

4. 任务被 Agent 执行完成（status → done）
   → 任务有 result_summary: { parameters: {工期: 7, 成本: 300, 安全系数: 1.5} }

5. 【关键】所有任务完成时，自动捕获方案
   → 收集该轮所有 tasks 的 result_summary
   → 收集该轮所有 projects 的 ID
   → 写入 solutions 表：
     {
       goal_id, round: 1, name: "方案A-快速修桥",
       parameters: {工期: 7, 成本: 300, 安全系数: 1.5},
       score: 78.5,
       project_ids: ["proj-xxx", "proj-yyy"],  ← 关联工程
       task_ids: ["task-111", "task-222"],      ← 关联任务
       constraints: {...}
     }

6. 比较引擎自动评分
   → 多维度加权计算 score
   → 更新解决方案 status（compliant/non_compliant）

7. Nexus 派发第二轮任务（方案B）
   → 不同思路：换场景、换工程组合、换约束
   → 重复步骤 3-6
   → solutions round: 2, name: "方案B-综合优化", parameters: {工期: 10, 成本: 250, 安全系数: 1.8}
   → project_ids/project_names 不同！task_ids 不同！

8. 重复直到满足结束条件：
   - 改进 < 5% → 提示用户确认
   - 用户手动选择"够了，选方案B"
   - 达到 max_rounds
```

---

## 三、优化模式完整数据流

```
1. 用户从探索模式选定方案B（最优方案）
   → 目标 mode 切换为 'optimization'
   → 继承方案B的参数和执行计划作为起点
   goals: { mode: 'optimization', optimization_target: 'overall', ... }

2. 读取方案B的执行计划，分阶段拆解
   → 阶段1：勘测调研（任务1、任务2）
   → 阶段2：基础建设（任务3、任务4）
   → 阶段3：主体施工（任务5、任务6）
   → 阶段4：收尾验收（任务7、任务8）

3. Nexus 派发第一阶段任务
   → 任务描述继承方案B的约束和目标
   → tasks: { goal_id, status: 'todo', category: 'phase-1-勘测' }

4. 第一阶段任务完成 → 自动捕获
   → solutions round: 3, name: "方案B-阶段1:勘测完成"
   → parameters: {勘测结果: "...", 发现风险: "地质条件复杂"}
   → project_ids: ["proj-phase1"], task_ids: ["task-1", "task-2"]
   → score: 根据阶段成果评估

5. 用户确认阶段成果 → 进入下一阶段
   → 读取上一阶段结果，调整下一阶段计划
   → 如果阶段1发现地质复杂 → 阶段2增加地基加固任务
   → 这就是"螺旋形"：根据上一轮结果动态调整下一轮计划

6. 重复 3-5 直到：
   - 所有阶段完成 → 目标达成
   - 预算/资源耗尽 → 暂停
   - 用户决定停止
```

---

## 四、数据库操作（每个操作的 SQL/ORM）

### 4.1 自动捕获方案（核心，Sprint 69 缺失的）

```python
# 触发时机：任务 status 变为 done 后
# 入口：task_manager.update_task_status() 或 project_executor 收集到 done 任务

def auto_capture_solution(goal_id: str, db: Session):
    """当目标下所有当前轮次任务完成时，自动捕获方案"""
    
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal or goal.mode not in ('exploration', 'optimization'):
        return
    
    # 获取本轮所有已完成任务
    goal_tasks = db.query(Task).filter(
        Task.goal_id == goal_id,
        Task.status == 'done'
    ).all()
    
    if not goal_tasks:
        return
    
    # 获取本轮所有工程
    goal_projects = db.query(Project).filter(
        Project.goal_id == goal_id
    ).all()
    
    # 从 tasks 的 result_summary 提取参数
    parameters = {}
    for task in goal_tasks:
        summary = json.loads(task.result_summary or '{}')
        if 'parameters' in summary:
            parameters.update(summary['parameters'])
    
    # 计算当前轮次
    existing = db.query(Solution).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.round.desc()).first()
    current_round = (existing.round if existing else 0) + 1
    
    # 获取本轮约束
    constraint_row = db.query(IterationConstraint).filter(
        IterationConstraint.goal_id == goal_id,
        IterationConstraint.round == current_round
    ).order_by(IterationConstraint.created_at.desc()).first()
    constraints = json.loads(constraint_row.constraints) if constraint_row else {}
    
    # 创建方案
    solution = Solution(
        id=f"sol-{uuid4().hex[:12]}",
        goal_id=goal_id,
        round=current_round,
        name=f"方案-{current_round}",  # 后续由 LLM 生成名称
        status='pending',
        parameters=parameters,
        dimensions=parameters,  # dimensions = parameters（默认）
        score=None,  # 由比较引擎计算
        is_optimal=False,
        project_ids=json.dumps([p.id for p in goal_projects]),  # ← 关联！
        task_ids=json.dumps([t.id for t in goal_tasks]),        # ← 关联！
        constraints=json.dumps(constraints),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(solution)
    db.commit()
    
    # 触发比较引擎
    compare_solutions(db, goal_id, solution.id)
```

### 4.2 比较引擎

```python
def compare_solutions(db: Session, goal_id: str, new_solution_id: str):
    """比较所有方案，更新评分和状态"""
    
    solutions = db.query(Solution).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.round.asc(), Solution.score.desc()).all()
    
    for sol in solutions:
        params = json.loads(sol.parameters or '{}')
        score = calculate_score(params, goal.optimization_target)
        sol.score = score
        sol.status = classify_solution(score)
    
    db.commit()

def calculate_score(params: dict, target: str) -> float:
    """多维度加权评分"""
    weights = {
        '工期': 0.35,
        '成本': 0.35,
        '安全系数': 0.30,
    }
    
    # 归一化 + 加权
    score = 0.0
    for key, weight in weights.items():
        if key in params:
            val = params[key]
            # 简单归一化：值越小越好（工期/成本）或越大越好（安全系数）
            if key == '安全系数':
                score += weight * min(val / 2.0, 1.0) * 100
            else:
                score += weight * max(1 - val / 50.0, 0) * 100
    return round(score, 1)

def classify_solution(score: float) -> str:
    if score >= 80: return 'compliant'
    if score >= 60: return 'non_compliant'
    return 'rejected'
```

### 4.3 约束自动调整

```python
def adjust_constraints_for_next_round(db: Session, goal_id: str, current_round: int):
    """根据上一轮结果自动调整约束"""
    
    prev_constraint = db.query(IterationConstraint).filter(
        IterationConstraint.goal_id == goal_id,
        IterationConstraint.round == current_round
    ).order_by(IterationConstraint.created_at.desc()).first()
    
    if not prev_constraint:
        return {"工期": "需设置", "成本": "需设置", "安全系数": "≥1.0"}
    
    prev = json.loads(prev_constraint.constraints)
    adjusted = {}
    
    for key, val in prev.items():
        if isinstance(val, (int, float)) and val > 0:
            if key in ('工期', 'duration'):
                adjusted[key] = round(val * 0.9, 2)
            elif key in ('成本', 'cost'):
                adjusted[key] = round(val * 0.9, 2)
            else:
                adjusted[key] = round(val * 0.95, 2)
    
    return adjusted
```

### 4.4 进度判断（优化模式）

```python
def check_optimization_progress(db: Session, goal_id: str) -> dict:
    """优化模式的进度判断：是否在向目标螺旋推进？"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    solutions = db.query(Solution).filter(
        Solution.goal_id == goal_id,
        Solution.score.isnot(None)
    ).order_by(Solution.round.desc()).all()
    
    if len(solutions) < 2:
        return {"done": False, "message": "至少需要 2 个阶段"}
    
    latest = solutions[0]
    prev = solutions[1]
    
    # 改进幅度：衡量是否在螺旋前进
    improvement = abs(latest.score - prev.score) / prev.score if prev.score > 0 else 1.0
    
    # 收敛判断（改进太小 → 进入瓶颈）
    threshold = goal.convergence_threshold or 0.05
    
    if improvement < 0.01:
        return {
            "done": False, 
            "requires_human": True, 
            "message": f"改进 {improvement:.1%}，进入瓶颈，是否调整方向？"
        }
    
    # 如果 score 在持续上升且达到目标线 → 完成
    if latest.score >= 90 and improvement < threshold:
        return {
            "done": True, 
            "message": f"评分 {latest.score} 已达目标，可收敛"
        }
    
    return {
        "done": False, 
        "improvement": improvement,
        "message": f"改进 {improvement:.1%}，继续推进"
    }
```

---

## 五、前端页面

### 5.1 GoalDetail 页面（探索/优化模式）

**顶部**：迭代控制面板
- 当前模式 Badge（探索模式/优化模式）
- 当前轮次
- 状态指示器（运行中/已暂停/已收敛/待用户确认）
- 操作按钮：下一轮 / 暂停 / 宣布收敛

**中部**：方案列表
- 表格：轮次 | 方案名 | 评分 | 状态 | 核心参数摘要 | 创建时间
- 点击方案名 → 展开详情面板

**方案详情面板**（展开后）：
- 完整参数表
- **关联工程列表**（名称、状态、点击可跳转）
- **关联任务列表**（名称、执行结果摘要、状态）
- 本轮约束条件
- 操作：标记最优 / 否决 / 删除

**底部**：收敛趋势图（优化模式时显示）
- 折线图：轮次 vs 评分
- 参数变化表

### 5.2 SolutionCenter 页面

- 目标筛选器（只筛选探索模式目标）
- 多维度对比表格
- 方案详情抽屉（含关联任务/工程）
- 收敛趋势图

---

## 六、Sprint 拆分

| Sprint | 内容 | 验收标准 |
|--------|------|----------|
| **76a** | 自动捕获逻辑 + DB 关联 | 任务 done → 方案自动生成，task_ids/project_ids 非 null |
| **76b** | 比较引擎 + 收敛判断 | 2 个方案 → 自动评分 + 最优标记 |
| **76c** | 约束调整 + 迭代回路 | 点击"下一轮" → 新约束注入任务描述 |
| **76d** | 前端方案详情页 | 能看到关联的工程和任务列表 |
| **76e** | 端到端闭环验证 | 跑一次完整探索→优化流程，数据全链路正确 |

---

## 七、验证标准（四板斧，缺一不可）

| 验证项 | 方法 | 通过标准 |
|--------|------|----------|
| 编译 | `npx tsc --noEmit` + `python -m py_compile` | 0 errors |
| API | curl 关键端点 | 200 + 正确 JSON 结构 |
| **数据** | 查 DB：`SELECT project_ids, task_ids FROM solutions` | **非 null，非空数组** |
| 页面 | 浏览器访问 | 方案详情能看到关联任务/工程 |
| **业务闭环** | 真的跑一个任务完成流程 | 方案自动生成，数据正确关联 |
