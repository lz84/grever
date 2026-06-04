# 双字段方案：保留 `depends_on` + 新增 `next_step`

> **日期**：2026-05-18
> **触发**：DAG 流程图箭头方向反复出错，根本原因是 `depends_on`（逆向依赖）不适合画图
> **核心思路**：保留控制逻辑字段，新增画图字段，双字段同步维护

---

## 一、为什么需要双字段

### `depends_on`（保留，控制逻辑用）

```python
project.fix2.depends_on = ["proj-dep-001"]
# 含义：fix2 依赖 dep-001，dep-001 必须先完成
# 用途：任务派发、阻塞检查、状态流转
```

- **必要**：调度器需要知道"我的前置条件是谁"
- **不适合画图**：方向反了，每次连线逻辑都要反转

### `next_step`（新增，DAG 画图用）

```python
project.dep-001.next_step = ["proj-fix2"]
# 含义：dep-001 完成后，下一步是 fix2
# 用途：DAG 箭头方向、流程图布局、UI 展示
```

- **适合画图**：箭头方向 = 自然阅读方向 = 执行顺序
- **不暴露给前端修改**：由后端自动同步，前端只读

### 双向链结构

```
fix2.depends_on = [dep]     ← 控制逻辑：fix2 依赖 dep
dep.next_step   = [fix2]    ← 画图逻辑：dep 下一步是 fix2

DAG:  Goal → dep → fix2
```

---

## 二、数据库改动

### 2.1 新增列（不删除旧列）

```sql
ALTER TABLE projects ADD COLUMN next_step TEXT DEFAULT '[]';
ALTER TABLE tasks    ADD COLUMN next_step TEXT DEFAULT '[]';
```

| 表 | 旧字段 | 新字段 | 说明 |
|---|--------|--------|------|
| `projects` | `depends_on` (Text/JSON) | **保留** | 控制逻辑 |
| `projects` | — | `next_step` (Text/JSON) | **新增**，画图用 |
| `tasks` | `depends_on` (Text/JSON) | **保留** | 控制逻辑 |
| `tasks` | — | `next_step` (Text/JSON) | **新增**，画图用 |

### 2.2 历史数据迁移（一次性）

从 `depends_on` 反向推导 `next_step`：

```python
def derive_next_step_from_depends_on(conn):
    """从 depends_on 推导 next_step"""

    # Projects
    projects = conn.execute(text(
        "SELECT id, depends_on FROM projects WHERE depends_on IS NOT NULL AND depends_on != '[]'"
    )).fetchall()

    next_steps: dict[str, list] = {}
    for pid, deps_raw in projects:
        deps = json.loads(deps_raw) if deps_raw else []
        for dep_id in deps:
            next_steps.setdefault(dep_id, []).append(pid)

    for pid, nxt in next_steps.items():
        conn.execute(text(
            "UPDATE projects SET next_step = :v WHERE id = :id"
        ), {"v": json.dumps(nxt), "id": pid})

    # Tasks — 同样逻辑
    tasks = conn.execute(text(
        "SELECT id, depends_on FROM tasks WHERE depends_on IS NOT NULL AND depends_on != '[]'"
    )).fetchall()

    next_steps = {}
    for tid, deps_raw in tasks:
        deps = json.loads(deps_raw) if deps_raw else []
        for dep_id in deps:
            next_steps.setdefault(dep_id, []).append(tid)

    for tid, nxt in next_steps.items():
        conn.execute(text(
            "UPDATE tasks SET next_step = :v WHERE id = :id"
        ), {"v": json.dumps(nxt), "id": tid})

    conn.commit()
```

---

## 三、后端改动

### 3.1 Model 改动

**`models/project.py`**：

```python
class Project(Base):
    # ... 现有字段 ...
    depends_on = Column(Text, nullable=True)   # 保留，JSON list
    next_step = Column(Text, default='[]')     # 新增，JSON list
```

**`models/task.py`**：同上。

### 3.2 写入时自动同步

**创建时**：

```python
def create_project(data, db):
    project = Project(**data)
    db.add(project)
    db.flush()  # 获取 project.id

    # 同步：每个 depends_on 的父节点，更新其 next_step
    for dep_id in project.depends_on:
        parent = db.query(Project).get(dep_id)
        if parent:
            parent_next = json.loads(parent.next_step) if parent.next_step else []
            if project.id not in parent_next:
                parent_next.append(project.id)
                parent.next_step = json.dumps(parent_next)

    db.commit()
    return project
```

**更新 depends_on 时**：

```python
def update_project_depends_on(project, new_depends_on, db):
    # 1. 清除旧的反向引用
    old_depends_on = json.loads(project.depends_on) if project.depends_on else []
    for dep_id in old_depends_on:
        parent = db.query(Project).get(dep_id)
        if parent:
            parent_next = json.loads(parent.next_step) if parent.next_step else []
            parent_next = [x for x in parent_next if x != project.id]
            parent.next_step = json.dumps(parent_next)

    # 2. 设置新的 depends_on
    project.depends_on = json.dumps(new_depends_on)

    # 3. 建立新的反向引用
    for dep_id in new_depends_on:
        parent = db.query(Project).get(dep_id)
        if parent:
            parent_next = json.loads(parent.next_step) if parent.next_step else []
            if project.id not in parent_next:
                parent_next.append(project.id)
                parent.next_step = json.dumps(parent_next)

    db.commit()
```

**删除时**：
- 删除 A 时，从 A.depends_on 中每个父节点的 next_step 里移除 A.id
- 从 A.next_step 中每个子节点的 depends_on 里移除 A.id

### 3.3 API 改动

| 端点 | 改动 |
|------|------|
| `GET /api/v1/projects/` | 返回时增加 `next_step` 字段 |
| `GET /api/v1/tasks/` | 返回时增加 `next_step` 字段 |
| `POST /api/v1/projects/` | 保持接收 `depends_on`，后端自动同步 `next_step` |
| `PUT /api/v1/projects/{id}` | 同上 |
| `POST /api/v1/tasks/` | 同上 |
| `PUT /api/v1/tasks/{id}` | 同上 |

**注意**：前端不需要（也不应该）直接修改 `next_step`，它是派生字段。

---

## 四、前端改动

### 4.1 类型定义（`utils/api.ts`）

```typescript
export interface Project {
  // ... 现有字段 ...
  next_step?: string[];  // 新增
}

export interface Task {
  // ... 现有字段 ...
  next_step?: string[];  // 新增
}
```

### 4.2 DAG 连线逻辑（`GoalDecomposePage.tsx`）

**旧逻辑**（用 `depends_on`，需要反向查找，容易出错）：
```typescript
// 需要遍历所有节点找谁依赖谁 → 容易搞反
```

**新逻辑**（用 `next_step`，正向遍历）：

```typescript
// 1. 工程之间的依赖箭头（用 next_step，正向）
projects.forEach(p => {
  const nextSteps = (p as any).next_step || []
  nextSteps.forEach(nextId => {
    allEdges.push({
      id: `edge-dep-${p.id}-${nextId}`,
      source: p.id,
      target: nextId,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: '#f59e0b', strokeWidth: 2 },
    })
  })
})

// 2. Goal → 根工程（没有父工程的工程）
projects.forEach(p => {
  const deps = (p as any).depends_on || []
  if (deps.length === 0) {
    allEdges.push({
      id: `edge-goal-${p.id}`,
      source: goal.id,
      target: p.id,
      animated: false,
      style: { stroke: '#a78bfa', strokeWidth: 2, strokeDasharray: '4 4' },
    })
  }
})

// 3. 任务之间的依赖箭头（用 next_step）
tasks.forEach(t => {
  const nextSteps = (t as any).next_step || []
  nextSteps.forEach(nextId => {
    allEdges.push({
      id: `edge-task-${t.id}-${nextId}`,
      source: t.id,
      target: nextId,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: '#a78bfa', strokeWidth: 1.5 },
    })
  })
})

// 4. Project → 根任务（同一工程下无依赖的任务）
projects.forEach(p => {
  const projTasks = tasks.filter(t => t.project_id === p.id)
  projTasks.forEach(t => {
    const deps = (t as any).depends_on || (t as any).dependency_ids || []
    const isRootTask = !deps.some(d => projTasks.some(pt => pt.id === d))
    if (isRootTask) {
      allEdges.push({
        id: `edge-proj-${p.id}-${t.id}`,
        source: p.id,
        target: t.id,
        animated: false,
        style: { stroke: '#34d399', strokeWidth: 1.5, strokeDasharray: '4 4' },
      })
    }
  })
})
```

### 4.3 编辑依赖关系

**UI 保持不变**：用户选择"依赖哪些任务"（修改 `depends_on`）。

后端收到 `depends_on` 更新后，自动同步 `next_step`。

前端不需要知道 `next_step` 的存在。

---

## 五、实施步骤

| 步骤 | 内容 | 预估时间 | 风险 |
|------|------|----------|------|
| 1 | SQL: 添加 `next_step` 列 | 5 min | 低 |
| 2 | Python 脚本: 从 depends_on 推导 next_step | 15 min | 中 |
| 3 | 后端 models: 加 `next_step` 字段 | 10 min | 低 |
| 4 | 后端 API: 写入/更新时同步 next_step | 30 min | 中 |
| 5 | 前端 api.ts: 类型增加 `next_step` | 5 min | 低 |
| 6 | 前端 DAG 连线: 改用 `next_step` | 20 min | 中 |
| 7 | 端到端验证 | 15 min | — |

**总计**：约 1.5-2 小时

---

## 六、关键原则

1. **`depends_on` 是权威**：控制逻辑、阻塞检查、状态流转只看 `depends_on`
2. **`next_step` 是派生**：只用于画图，不直接修改，由后端自动维护
3. **前端不写 `next_step`**：前端只改 `depends_on`，`next_step` 由后端计算返回
4. **事务一致性**：`depends_on` 和 `next_step` 的更新在同一个事务中
5. **不删除 `depends_on`**：向后兼容，旧代码继续工作
