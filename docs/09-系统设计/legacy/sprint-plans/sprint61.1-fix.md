# Sprint 61.1: 数据源统一 + 系统管理面

> 日期: 2026-05-07 | 状态: 待评审 | 优先级: P0（阻断 Sprint 63）

---

## 一、问题诊断

### 1.1 当前实际状态（2026-05-07 12:47 现场确认）

| 指标 | 实际情况 | 问题 |
|------|----------|------|
| agents DB | 5 条记录 ✅ | DB 持久化已正常工作 |
| 4/5 Worker 心跳 | 51min 前停止 | kouzi 活着，其余 4 个静默 |
| verifying 僵尸任务 | 5 个（昨天 17:xx）| 卡住，无法自动恢复 |
| blocked 任务 | 1 个（昨天 09:43）| |
| timeout 任务 | 1 个（昨天 18:19）| |
| 管理面板 | 无 | 人无法手动干预 |

### 1.2 重新评估

**DB 持久化问题已在 Sprint 61 修复**。`AgentRegistry` 直接写 DB，5 个 agent 全在 DB。

**真正的问题是**：
1. **僵尸任务无自动恢复**（verifying/blocked/timeout 卡住）
2. **人无法自救**（无管理面板）
3. **Worker 断连无自动回收**（4 个 Worker 静默 51min）

---

## 二、目标

| 目标 | 说明 |
|------|------|
| **彻底消灭内存缓存** | Agent 注册/心跳/状态全部以 DB 为唯一数据源 |
| **系统管理面板** | 人在页面上能重启 agent、重置任务、清理僵尸 |
| **自动恢复** | Worker 断连后自动回收任务、重新派发 |
| **僵尸任务清理** | 启动时自动清理 assigned_agent 不存在的任务 |

---

## 三、任务拆分

### 3.1 Phase 1: 僵尸任务自动清理 + 离线 Worker 回收（~0.5 天）

> 当前状态：5 个 verifying 僵尸任务 + 1 个 blocked + 1 个 timeout，都是昨天卡住的。
> DB 持久化已在 Sprint 61 修复（5 个 agent 全在 DB），不再需要修数据源。

#### T1.1: 僵尸任务自动清理脚本

**文件**: `packages/server/src/reins/recovery.py`（新建）

```python
"""
Nexus 故障恢复脚本
- 清理卡在 verifying/blocked/timeout 超过阈值时间的任务
- 回收 offline Worker 的 in_progress 任务
"""
from reins.database import get_db_session
from sqlalchemy import text
from datetime import datetime, timedelta

VERIFICATION_TIMEOUT_HOURS = 1  # verifying 超过 1 小时重置
BLOCK_TIMEOUT_HOURS = 24        # blocked/timeout 超过 24 小时重置

def cleanup_zombie_tasks(db_session):
    """清理僵尸任务"""
    now = datetime.now()
    cleaned = []
    
    # 清理 verifying 僵尸（超过阈值 → todo）
    verifying_deadline = now - timedelta(hours=VERIFICATION_TIMEOUT_HOURS)
    result = db_session.execute(text("""
        SELECT id, title, assigned_agent, updated_at
        FROM tasks
        WHERE status = 'verifying'
        AND updated_at < :deadline
    """), {'deadline': verifying_deadline.isoformat()})
    zombie_verifying = result.fetchall()
    if zombie_verifying:
        ids = [r[0] for r in zombie_verifying]
        db_session.execute(text("""
            UPDATE tasks
            SET status = 'todo', assigned_agent = NULL, updated_at = :now
            WHERE id IN :ids
        """), {'ids': tuple(ids), 'now': now.isoformat()})
        cleaned.append(f'verifying: {len(zombie_verifying)} tasks')
    
    # 清理 blocked/timeout 僵尸
    block_deadline = now - timedelta(hours=BLOCK_TIMEOUT_HOURS)
    result = db_session.execute(text("""
        SELECT id, title, status, updated_at
        FROM tasks
        WHERE status IN ('blocked', 'timeout')
        AND updated_at < :deadline
    """), {'deadline': block_deadline.isoformat()})
    zombie_blocked = result.fetchall()
    if zombie_blocked:
        ids = [r[0] for r in zombie_blocked]
        db_session.execute(text("""
            UPDATE tasks
            SET status = 'todo', assigned_agent = NULL, updated_at = :now
            WHERE id IN :ids
        """), {'ids': tuple(ids), 'now': now.isoformat()})
        cleaned.append(f'blocked/timeout: {len(zombie_blocked)} tasks')
    
    db_session.commit()
    return cleaned

def recover_offline_agent_tasks(db_session, offline_threshold_minutes=90):
    """回收离线 Worker 的任务，标记为 offline"""
    deadline = datetime.now() - timedelta(minutes=offline_threshold_minutes)
    
    # 找离线超时的 agent
    result = db_session.execute(text("""
        SELECT id, name FROM agents
        WHERE last_heartbeat < :deadline
        AND status != 'offline'
    """), {'deadline': deadline.isoformat()})
    offline_agents = result.fetchall()
    recovered = []
    now = datetime.now()
    
    for agent in offline_agents:
        # 回收该 agent 的卡住任务
        result2 = db_session.execute(text("""
            UPDATE tasks
            SET status = 'todo', assigned_agent = NULL, updated_at = :now
            WHERE assigned_agent = :agent_id
            AND status IN ('in_progress', 'verifying')
        """), {'agent_id': agent[0], 'now': now.isoformat()})
        if result2.rowcount > 0:
            recovered.append(f'{agent[1]}: {result2.rowcount} tasks')
        
        # 标记 agent 为 offline
        db_session.execute(text("""
            UPDATE agents SET status = 'offline', updated_at = :now
            WHERE id = :agent_id
        """), {'agent_id': agent[0], 'now': now.isoformat()})
    
    db_session.commit()
    return recovered
```

**Done Criteria**:
- [ ] 清理 5 个 verifying 僵尸任务 → todo
- [ ] 清理 1 个 blocked 任务 → todo
- [ ] 清理 1 个 timeout 任务 → todo
- [ ] 标记 4 个离线 agent 为 offline
- [ ] curl 验证任务状态已更新

#### T1.2: 启动时自动执行清理

**文件**: `packages/server/src/reins/api/server.py` — `@app.on_event("startup")` 中加入

```python
@app.on_event("startup")
async def startup_event():
    # ... 现有 startup 代码 ...
    
    # Sprint 61.1: 启动时自动清理僵尸任务 + 回收离线任务
    from reins.recovery import cleanup_zombie_tasks, recover_offline_agent_tasks
    from reins.database import get_db_session
    try:
        db = get_db_session()
        try:
            cleaned = cleanup_zombie_tasks(db)
            for msg in cleaned:
                print(f"[Sprint61.1] 清理: {msg}")
            recovered = recover_offline_agent_tasks(db)
            for msg in recovered:
                print(f"[Sprint61.1] 回收: {msg}")
        finally:
            db.close()
    except Exception as e:
        print(f"[Sprint61.1] 启动清理失败: {e}")
```

**Done Criteria**:
- [ ] 启动日志中有清理记录
- [ ] 重启后 verifying 僵尸任务为 0

### 3.2 Phase 2: 系统管理面板（~0.5 天）

#### T2.1: Agent 管理 API

**文件**: 新增 `packages/server/src/reins/api/admin.py`

```python
# POST /api/v1/admin/agents/{id}/force-offline
# 强制将 agent 标记为 offline
# 触发其 in_progress 任务回滚为 todo

# POST /api/v1/admin/agents/{id}/reregister
# 重新注册 agent（清除旧状态，重新初始化）

# POST /api/v1/admin/tasks/{id}/reset
# 重置任务状态（in_progress → todo, verifying → todo 等）

# POST /api/v1/admin/tasks/{id}/reassign
# 重新分配任务给另一个 agent

# POST /api/v1/admin/cleanup/zombie-tasks
# 清理所有 assigned_agent 不存在或 agent 已下线的 in_progress 任务
```

#### T2.2: Agent 管理页面

**文件**: 新增 `packages/ui/src/pages/system/AgentManagement.tsx`

```
┌────────────────────────────────────────────────────────────┐
│  系统管理 › Agent 管理                                      │
│                                                            │
│  [全部重注册]  [清理僵尸任务]  [强制全部下线]                │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Agent  │ 状态      │ 最后心跳   │ 任务 │ 操作       │ │
│  ├────────┼───────────┼────────────┼──────┼────────────┤ │
│  │ kouzi  │ ✅ online  │ 11:25      │ 0    │ [重注册]   │ │
│  │        │          │            │      │ [强制下线] │ │
│  ├────────┼───────────┼────────────┼──────┼────────────┤ │
│  │ guzi   │ ⚠️ offline│ 昨天 20:27 │ 0    │ [重注册]   │ │
│  │        │          │            │      │ [强制下线] │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

#### T2.3: 任务管理页面

**文件**: 新增 `packages/ui/src/pages/system/TaskManagement.tsx`

```
┌────────────────────────────────────────────────────────────┐
│  系统管理 › 任务管理                                        │
│                                                            │
│  [重置全部卡住任务]  [清理僵尸任务]                          │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 任务 ID   │ 标题       │ 状态        │ 操作           │ │
│  ├───────────┼────────────┼─────────────┼────────────────┤ │
│  │ task-001  │ ...        │ in_progress │ [重置→todo]    │ │
│  │ task-c1.. │ ...        │ in_progress │ [重置→todo]    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  提示: 共 8 个卡住的 in_progress 任务                        │
└────────────────────────────────────────────────────────────┘
```

### 3.3 Phase 3: 自动恢复机制（~0.5 天）

#### T3.1: 启动时僵尸任务清理

**文件**: `packages/server/src/reins/background_tasks.py` 或新增 `reins/recovery.py`

```python
async def cleanup_zombie_tasks(db):
    """
    启动时清理:
    1. in_progress 任务中 assigned_agent 不存在的 → 重置为 todo
    2. in_progress 任务中 agent 已 offline 超过 90s 的 → 重置为 todo
    3. verifying 任务中 verifier agent 不存在的 → 重置为 todo
    """
    # 获取所有在线 agent ID
    online_agents = set(a.id for a in db.list_agents(status='online'))
    
    # 找到僵尸任务
    zombie_tasks = db.execute("""
        SELECT id, title, assigned_agent, status
        FROM tasks
        WHERE status IN ('in_progress', 'verifying')
        AND assigned_agent NOT IN :online_agents
    """, {'online_agents': tuple(online_agents)})
    
    # 重置
    for task in zombie_tasks:
        db.update_task(task.id, status='todo', assigned_agent=None)
        log.info(f"清理僵尸任务: {task.id} ({task.title})")
```

#### T3.2: 心跳超时自动恢复

**文件**: `packages/server/src/reins/scheduler/health_manager.py`

当前已有离线判定（90s），但离线后没有任何动作。加上自动恢复：

```python
async def check_agent_health():
    for agent in agents:
        if agent.offline_seconds > 90:
            # 1. 标记 offline
            db.update_agent(agent.id, status='offline')
            
            # 2. 回收其 in_progress 任务
            stuck_tasks = db.get_tasks(assigned_to=agent.id, status='in_progress')
            for task in stuck_tasks:
                db.update_task(task.id, status='todo', assigned_agent=None)
                log.info(f"Agent {agent.id} 离线，回收任务 {task.id}")
```

---

## 四、执行顺序

```
Phase 1 (T1.1 → T1.2 → T1.3)  → 先修数据源，否则后面都是白搭
    ↓
Phase 3 (T3.1 → T3.2)         → 自动恢复，解决当前卡住的问题
    ↓
Phase 2 (T2.1 → T2.2 → T2.3)  → 管理面板，让人能自救
```

**为什么 Phase 3 在 Phase 2 之前**：因为当前 8 个僵尸任务 + 4 个死掉 Worker 是火烧眉毛的事，自动恢复能立刻解决。管理面板是让人以后能自己处理。

---

## 五、Sprint 61.1 Done Criteria

- [ ] agents DB 记录数 = API 返回数（双数据源问题修复）
- [ ] 后端重启后 agent 数据不丢失
- [ ] 0 处 `self.agents[` 直接内存访问
- [ ] curl 验证: 注册 → DB 有记录 → 心跳 → DB 更新 last_heartbeat
- [ ] 启动时自动清理 8 个僵尸任务 → 重置为 todo
- [ ] Worker 断连 90s 后自动回收任务
- [ ] Agent 管理页面能正常显示 + 操作
- [ ] 任务管理页面能正常显示 + 重置操作
- [ ] `npx tsc --noEmit` 0 errors（前端）
- [ ] `npm run build` 成功
- [ ] 页面验证: 所有管理操作能正常执行
