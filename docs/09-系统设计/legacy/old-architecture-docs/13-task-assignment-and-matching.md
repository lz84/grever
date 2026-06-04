# Nexus 任务分配与匹配引擎架构

**版本**: v1.0  
**作者**: 刚子  
**日期**: 2026-05-20  
**状态**: 已确认，立即执行  

---

## 1. 三条铁律

### 铁律一：统一匹配引擎，调用时机是结构分解后

| ❌ 错误做法 | ✅ 正确做法 |
|---|---|
| 每个 task 创建时自动分配 | Goal/Project 完成结构分解后，**统一触发** `assign_pending_tasks()` |
| 心跳时各自拉任务 | 一次性匹配所有下属任务，不是逐条分配 |
| 在 CRUD 文件里写分配逻辑 | 匹配引擎是**唯一入口**，禁止分散 |

**调用时机**:
```
Goal 创建
  → decompose（结构分解，生成 Projects + Tasks）
    → 统一触发 TaskAssigner.assign_pending_tasks()
      → 对每个 todo 任务：读取 capability_tags → 匹配引擎 → 分配 agent
```

### 铁律二：创建 Task/Project 必须设置 depends_on + capability_tags

**创建 Task 时必填字段**：
| 字段 | 用途 | 示例 |
|---|---|---|
| `depends_on` | DAG 执行顺序，决定哪个任务先跑 | `["task-abc123"]` |
| `capability_tags` | 匹配引擎的输入，四维标签 | `{"technical": ["python", "fastapi"]}` |
| `assigned_agent` | **不填**，由匹配引擎决定 | `null` |

**depends_on 设置规则**：
- 同一个 Project 内，有前后依赖关系的任务必须设置
- 无依赖的任务设为空数组 `[]`
- 跨 Project 依赖由 Project 级别的依赖关系控制

**capability_tags 四维结构**：
| 维度 | 说明 | 示例 |
|---|---|---|
| `business` | 业务领域 | `["financial", "healthcare"]` |
| `professional` | 专业技能 | `["data_analysis", "report_writing"]` |
| `technical` | 技术栈 | `["python", "react", "sql"]` |
| `management` | 管理能力 | `["project_management", "stakeholder"]` |

### 铁律三：匹配逻辑绝对集中

**唯一入口**：`scheduler/task_assigner.py` → `TaskAssigner.assign_pending_tasks()`

**调用链路**：
```
assign_pending_tasks()
  → _assign_by_capability(conn, capability_tags)  # 有标签时
    → match_for_task(capability_tags)             # 匹配引擎
      → match() → _get_online_agents() + _tags()  # 能力打分
  → _assign_agent(db)                             # 无标签时的兜底
```

**禁止分散的位置**：
- ❌ `tasks_crud.py` — 已删除 `_assign_agent(db)` 自动分配（commit e3758eb）
- ❌ `heartbeat_routes.py` — 只负责返回已分配任务，不分配新任务
- ❌ 任何 CRUD 文件 — 不写任何分配逻辑

---

## 2. 匹配引擎设计（agent_matcher.py）

### 2.1 核心函数

```python
def match_for_task(tags: Dict) -> List[Dict]:
    """任务匹配：min_score=0.5, limit=3"""
    return match(tags, min_score=0.5, limit=3)

def match(capability_tags: Dict, min_score: float, limit: int) -> List[Dict]:
    """匹配所有在线 Agent，返回按分数排序的结果"""
    required = _tags(capability_tags)  # 展平为标签集合
    for agent in _get_online_agents():
        agent_tags = _tags(agent["capability_tags"])
        matched = required & agent_tags
        score = sum(weight.get(t, 1.0) for t in matched) / len(required)
        if score >= min_score:
            results.append({...})
    return sorted(results, key=lambda x: x["score"], reverse=True)
```

### 2.2 打分公式

```
score = Σ(weight[tag] for tag in matched_tags) / len(required_tags)
```

- `matched_tags`: 任务需求与 Agent 能力的交集
- `weight[tag]`: 标签权重，来自 `agent_tag_weights` 表
- 默认权重 1.0，完成任务后 +0.1，30/60/90 天过期衰减

### 2.3 未来扩展点

| 扩展项 | 当前状态 | 计划 |
|---|---|---|
| 能力标签匹配 | ✅ 已实现 | 保持核心 |
| 负载因子 | ✅ 已有 | 集成到打分公式 |
| Agent 在线状态 | ✅ 已有 | 过滤条件 |
| 信用评分 | ❌ 未实现 | 未来加入打分 |
| 响应时间 | ❌ 未实现 | 未来加入打分 |
| 历史成功率 | ❌ 未实现 | 未来加入打分 |

---

## 3. TaskAssigner.assign_pending_tasks() 详解

### 3.1 执行逻辑

```sql
-- 查询所有待分配任务（依赖全部完成 + 优先级排序）
SELECT t.id, t.title, t.priority, t.assigned_agent, t.capability_tags
FROM tasks t
WHERE t.status IN ('todo', 'pending')
  AND (t.assigned_agent IS NULL OR EXISTS (
      SELECT 1 FROM agents a 
      WHERE a.id = t.assigned_agent AND a.health_status != 'online'
  ))
  AND NOT EXISTS (
      SELECT 1 FROM task_dependencies td
      JOIN tasks dep ON td.dependency_id = dep.id
      WHERE td.task_id = t.id AND dep.status != 'done'
  )
ORDER BY priority, t.created_at ASC
```

### 3.2 分配流程

```
1. 查询待分配任务（依赖已满足、优先级排序）
2. 对每个任务：
   a. 解析 capability_tags
   b. _assign_by_capability() → 匹配引擎选 Agent
   c. 检查 Agent 是否有空余 slot
   d. 分配任务：UPDATE tasks SET status='in_progress', assigned_agent=...
3. 批量更新 Agent 的 current_tasks + load
4. 返回 assigned_count
```

---

## 4. 已知问题与修复

### 4.1 tasks_crud.py 自动分配已删除（2026-05-20）

**问题**：`tasks_crud.py` 创建任务时调用 `_assign_agent(db)` 自动分配，绕过了匹配引擎。

**修复**：commit `e3758eb` — 删除自动分配逻辑，`assigned_agent` 保持 `NULL`。

### 4.2 心跳接口不分配新任务

**事实**：`_agents_heartbeat_routes.py` 的 heartbeat 接口只查询 `assigned_agent=:aid` 的已分配任务，**不会自动分配新任务**。

**影响**：`assigned_agent=NULL` 的任务永远不会被任何 Agent 捡到，必须由 `assign_pending_tasks()` 统一分配。

---

## 5. 开发者指南

### 5.1 创建任务的正确姿势

```python
# ✅ 正确
task_data = {
    "project_id": "proj-xxx",
    "goal_id": "goal-xxx",
    "title": "编写用户认证模块",
    "description": "...",
    "priority": "high",
    "depends_on": ["task-abc123"],  # ← 必填
    "capability_tags": {            # ← 必填
        "technical": ["python", "fastapi", "jwt"],
        "professional": ["security"]
    },
    "acceptance_criteria": {...}   # ← 必填
}
# assigned_agent 不传，由匹配引擎决定

# ❌ 错误：指定 assigned_agent
task_data["assigned_agent"] = "mazi-uuid"  # 除非确实需要指定

# ❌ 错误：不设置 depends_on
task_data["depends_on"] = []  # 即使没有依赖也要显式设置

# ❌ 错误：不设置 capability_tags
# 匹配引擎无法工作，会 fallback 到负载选择
```

### 5.2 触发统一分配的时机

| 场景 | 触发方式 |
|---|---|
| Goal 分解完成 | `POST /goals/{id}/decompose` 后自动调用 |
| Project 创建完成 | 调用 `TaskAssigner.assign_pending_tasks()` |
| 手动重新分配 | `POST /scheduler/assign` |
| Agent 重新上线 | HeartbeatDetector 检测到后调用 |

---

## 6. 相关文件

| 文件 | 职责 |
|---|---|
| `scheduler/task_assigner.py` | 统一分配入口，`assign_pending_tasks()` |
| `services/agent_matcher.py` | 匹配引擎，`match_for_task()` |
| `services/auto_tagging.py` | 任务完成后自动更新 Agent 标签 |
| `api/tasks_crud.py` | 任务 CRUD（不写分配逻辑） |
| `api/_agents_heartbeat_routes.py` | 心跳接口（只返回已分配任务） |
