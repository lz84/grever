# Nexus 智能体管理、驾驭、编排架构文档

> 生成时间: 2026-05-09  
> 代码库: `D:\work\research\agents-nexus`

---

## 一、核心实体

### 1.1 实体关系总览

```
Goal (目标)
  └── Project (项目/工程)
       ├── Task (任务)
       │    ├── depends_on → Task
       │    ├── assigned_agent → Agent
       │    └── verifier_agent_id → Agent
       ├── workflow_id → Workflow
       └── matched_scenario_id → Scenario

Agent (智能体)
  ├── agent_id (PK)
  ├── capabilities (JSON 数组)
  ├── status: online | offline | busy | idle
  ├── trigger_mode: polling | sse
  ├── load (0-100)
  ├── current_tasks
  ├── max_concurrent_tasks
  └── health_status

Workflow (工作流)
  ├── WorkflowStep (步骤)
  │    ├── depends_on → [Step ID]
  │    ├── agent_type → Agent
  │    └── status: pending | running | done | failed
  └── 实例化为 Project

Scenario (场景)
  ├── category (分类)
  ├── template_id → Workflow
  └── ScenarioStep (场景步骤)

Dispute (争议)
  ├── type: goal_conflict | resource_competition | execution_failure
  ├── status: open | resolved | escalated
  └── resolver → Agent
```

---

## 二、6 大核心组件

### 2.1 ReinsServer — 中枢大脑

**位置**: `reins/__init__.py`  
**职责**: 整合 6 大核心管理职责

```python
class ReinsServer:
    """Nexus 服务端主类"""
    
    # 持久化仓库（DB 驱动）
    _goal_repository
    _project_repository  
    _task_repository
    _agent_repository
    _dispute_repository
    
    # 管理器
    task_manager          # 任务管理器
    goal_manager          # 目标管理器（含状态级联）
    project_manager       # 项目管理器
    agent_registry        # Agent 注册表（内存+DB）
    agent_discovery       # Agent 发现（按能力/负载匹配）
    dispute_manager       # 争议管理器
    
    # 辅助组件
    tracker               # 执行追踪
    _grasp_client         # Grasp 知识客户端
```

### 2.2 AgentRegistry — 智能体注册中心

**位置**: `reins/manager/agent_registry.py`

| 方法 | 说明 |
|------|------|
| `register(agent_id, name, capabilities, ...)` | 注册/更新 Agent（UPSERT） |
| `get_agent(agent_id)` | 从 DB 查询 Agent 信息 |
| `list_agents()` | 列出所有 Agent |
| `update_status(agent_id, status)` | 更新 Agent 状态 |
| `update_load(agent_id, load, current_tasks)` | 更新负载（同时写 DB + 内存） |
| `heartbeat_agent(agent_id, status_dict)` | 心跳处理（含 DB 写入） |
| `_db_current_tasks(agent_id)` | 从 DB 查实际 in_progress 任务数 |

**心跳超时**: 90 秒无心跳 → 标记 offline

### 2.3 AgentDiscovery — 智能体发现与匹配

**位置**: `reins/manager/agent_discovery.py`

**匹配策略** (按优先级):
1. **能力匹配**: Agent.capabilities ⊇ Task.required_capabilities
2. **负载均衡**: 选 `load_score` 最低的合格 Agent
3. **亲和性匹配**: 优先分配给已处理过同项目任务的 Agent
4. **冲突避免**: 排除被争议中的 Agent

```python
def find_best_agent(capabilities, exclude_agents=None, task_id=None):
    """找到最合适的 Agent"""
    candidates = self._filter_by_capability(capabilities)
    candidates = self._filter_by_availability(candidates, exclude_agents)
    candidates = self._sort_by_load(candidates)  # 低负载优先
    return candidates[0] if candidates else None
```

### 2.4 GoalManager — 目标管理器

**位置**: `reins/manager/goal_manager.py`

**核心职责**:
- 目标创建、查询、状态管理
- **状态级联**: Goal → Project → Task 自动传播
- 目标分解: Goal → Task 列表（通过 LLM）
- 进度计算: 基于子任务完成率

### 2.5 TaskManager — 任务管理器

**位置**: `reins/manager/task_manager.py`

**核心职责**:
- 任务 CRUD
- 状态机管理（todo → in_progress → done/failed）
- 任务依赖解析（DAG）
- 任务派发（Assignment）

### 2.6 DisputeManager — 争议管理器

**位置**: `reins/manager/dispute_manager.py`

**争议类型**:
| 类型 | 说明 |
|------|------|
| goal_conflict | 目标冲突（两个目标竞争同一资源） |
| resource_competition | 资源竞争（多个任务竞争同一 Agent） |
| execution_failure | 执行失败（任务执行结果争议） |

---

## 三、核心流程

### 3.1 目标分解流程 (Goal Decomposition)

```
1. 用户创建 Goal
      ↓
2. LLM 分解 Goal → Workflow (模板)
      ↓
3. 实例化 Workflow → Project + Tasks
      ↓
4. Task 进入待派发队列 (status=todo)
      ↓
5. Agent 心跳时领取任务
      ↓
6. Agent 执行 → 上报完成
      ↓
7. Verifier Agent 验证结果
      ↓
8. 全部 Task done → Project completed → Goal completed
```

### 3.2 心跳派发流程 (Heartbeat Dispatch)

```
Agent ──POST /api/v1/agents/{id}/heartbeat──→ Server
                                                    ↓
                                          1. 写入 heartbeat_logs
                                                    ↓
                                          2. 检查模型连通性
                                          (GET {agent_address}/health)
                                                    ↓
                                          3. 从 DB 同步 current_tasks
                                          (MAK-238: 内存↔DB 校准)
                                                    ↓
                                          4. 查询 pending 任务
                                          WHERE assigned_agent = :id
                                            AND status IN ('todo','pending')
                                                    ↓
                                          5. 能力匹配过滤
                                          (matches_capabilities)
                                                    ↓
                                          6. 负载检查
                                          (current_tasks < max_concurrent)
                                                    ↓
                                          7. 分配任务 → UPDATE DB
                                          (status='in_progress')
                                                    ↓
                                          8. 更新 Agent current_tasks + load
                                                    ↓
                                返回 {assigned_tasks: [...]} ← Agent 领取
```

### 3.3 任务状态机

```
                ┌─────────┐
                │  todo   │
                └────┬────┘
                     │ 派发
                ┌────▼────────┐
                │ in_progress │
                └────┬────────┘
                     │ 完成
                ┌────▼─────┐
                │  done    │
                └──────────┘

    失败路径: in_progress → failed
    阻塞路径: todo/in_progress → blocked
    审核路径: in_progress → review_needed → done/failed
    验证路径: done → verifying → done
    超时路径: in_progress → timeout
```

### 3.4 故障恢复流程 (Recovery)

```
周期性 Recovery (每 5 分钟)
    ↓
1. cleanup_zombie_tasks()
   - verifying > 1h → todo
   - blocked/timeout > 24h → todo
    ↓
2. recover_offline_agents()
   - 心跳 > 90min → 标记 offline
   - 回收其 in_progress 任务 → todo
   - 释放到任务池重新派发
    ↓
3. update_agent_load_from_db()
   - 从 DB 重新计算所有 Agent 的 load/current_tasks
```

### 3.5 Worker 生命周期

```
启动 Worker (agent_worker.py)
    ↓
循环:
  1. POST /heartbeat → 领取 assigned_tasks
  2. 如果有任务:
     a. spawn sub-agent 执行
     b. POST /tasks/{id}/progress (10%→50%→90%)
     c. POST /tasks/{id}/complete (100%)
  3. 如果没有任务:
     等待 HEARTBEAT_INTERVAL (30s)
  4. 心跳失败:
     重试 5 次 → 停止
```

---

## 四、数据库 Schema

### 4.1 核心表

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `agents` | Agent 注册 | id, name, capabilities(JSON), status, load, current_tasks |
| `goals` | 目标 | id, title, description, parent_id, status, verifier_agent_id |
| `projects` | 项目/工程 | id, name, goal_id, status, verifier_agent_id, workflow_id |
| `tasks` | 任务 | id, title, description, project_id, assigned_agent, status, depends_on(JSON) |
| `workflows` | 工作流模板 | id, name, description, status |
| `workflow_steps` | 工作流步骤 | id, workflow_id, name, agent_type, depends_on(JSON) |
| `scenarios` | 场景模板 | id, name, category, template_id |
| `disputes` | 争议 | id, type, status, resolver_agent_id |
| `heartbeat_logs` | 心跳日志 | id, agent_id, status, load, current_tasks, raw_payload |
| `execution_logs` | 执行日志 | id, agent_id, action, status, input, output |
| `scheduler_log` | 调度日志 | id, tick_number, agents_online, tasks_assigned |

### 4.2 索引

```sql
idx_agents_status          -- agents(status)
idx_tasks_project_id       -- tasks(project_id)
idx_tasks_assigned_agent   -- tasks(assigned_agent, status)
idx_tasks_status           -- tasks(status)
idx_tasks_project_status   -- tasks(project_id, status)
idx_projects_goal_id       -- projects(goal_id)
idx_heartbeat_logs_agent   -- heartbeat_logs(agent_id, timestamp DESC)
```

---

## 五、API 端点

### 5.1 Agent 管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents` | GET | 列出所有 Agent |
| `/api/v1/agents/{id}` | GET | 获取 Agent 详情 |
| `/api/v1/agents/{id}/heartbeat` | POST | 心跳 + 任务派发 |
| `/api/v1/agents/{id}/execution-logs` | GET | 执行日志 |
| `/api/v1/agents/{id}/heartbeat_logs` | GET | 心跳日志 |

### 5.2 任务管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/tasks` | GET | 列出任务（支持 project_id 过滤） |
| `/api/v1/tasks/{id}` | GET | 获取任务详情 |
| `/api/v1/tasks/{id}/complete` | POST | 完成任务上报 |
| `/api/v1/tasks/{id}/fail` | POST | 任务失败上报 |
| `/api/v1/tasks/{id}/progress` | POST | 任务进度上报 |
| `/api/v1/tasks/{id}/restart` | POST | 重启任务 |
| `/api/v1/tasks/{id}/comments` | POST | 添加评论 |

### 5.3 项目/目标

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/projects` | GET/POST | 列出/创建项目 |
| `/api/v1/projects/{id}` | GET/PUT/DELETE | 项目详情/更新/删除 |
| `/api/v1/projects/{id}/status` | PATCH | 更新项目状态 |
| `/api/v1/projects/{id}/diagram` | GET | 获取项目流程图 |
| `/api/v1/goals` | GET/POST | 列出/创建目标 |
| `/api/v1/goals/{id}` | GET | 目标详情 |

---

## 六、关键设计模式

### 6.1 DB 驱动 + 内存缓存

| 组件 | 数据来源 | 说明 |
|------|---------|------|
| Goals/Projects/Tasks | DB 直接读写 | 无内存缓存，每次查 DB |
| Agent | 内存 + DB 双写 | 心跳写内存 registry，定期从 DB 同步 |
| Disputes | DB 直接读写 | 无内存缓存 |

### 6.2 心跳驱动派发

任务派发**不依赖调度器轮询**，而是由 Agent 主动心跳时触发：
- Agent 每 10 秒心跳一次
- 心跳时 Server 检查该 Agent 是否有 pending 任务
- 有则分配并返回，无则返回空列表

### 6.3 能力匹配

任务分配时进行能力匹配过滤：
```python
def matches_capabilities(task, agent):
    """任务需要的能力 ⊆ Agent 能力集"""
    if not task.required_capabilities:
        return True  # 无要求则默认匹配
    return task_capabilities.issubset(agent_capabilities)
```

### 6.4 负载限流

- `max_concurrent_tasks`: Agent 最大并发任务数（默认 5）
- `load_threshold`: 负载阈值（默认 80%），超过则拒绝分配
- `current_tasks` 通过心跳实时更新

---

## 七、Worker (执行层)

### 7.1 Worker 定位

Worker 是 Nexus 的**执行层**，与 Server **进程分离**：

| 组件 | 职责 | 运行方式 |
|------|------|---------|
| Server (8094) | 任务派发、状态管理、调度 | 常驻进程 |
| Worker | 执行任务、模型调用 | 独立进程，每 Agent 一个 |

### 7.2 Worker 工作流

```
启动 → 注册心跳循环(30s)
  ↓
每次心跳:
  1. POST /heartbeat → 获取 assigned_tasks
  2. 如果有任务:
     - spawn sub-agent 执行
     - 等待 sub-agent 完成信号 (✅ / ❌)
     - POST /tasks/{id}/complete
  3. 等待 HEARTBEAT_INTERVAL(30s)
  4. 循环
```

### 7.3 Worker 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| HEARTBEAT_INTERVAL | 30s | 心跳间隔 |
| MAX_ERRORS | 5 | 最大连续错误次数 |
| timeout | 无 | 进程超时（不设超时保证持续运行） |

---

## 八、故障处理

### 8.1 Worker 死亡处理

| 场景 | 检测机制 | 处理方式 |
|------|---------|---------|
| Worker 被 kill | 心跳超 90s | 标记 offline，释放 in_progress 任务 |
| 任务卡在 verifying | periodic recovery (每 5 分钟) | 超 1h 重置为 todo |
| 任务卡在 blocked/timeout | periodic recovery | 超 24h 重置为 todo |

### 8.2 MAK-238 修复 (心跳 DB 同步)

在心跳入口从 DB 同步 `current_tasks`，防止内存缓存陈旧导致分配失败：
```python
# 心跳开始时强制从 DB 同步
_db_actual = db.execute(
    "SELECT COUNT(*) FROM tasks WHERE assigned_agent=:a AND status='in_progress'"
).fetchone()
if agent_info.current_tasks != _db_actual[0]:
    reins.agent_registry.update_load(agent_id, current_tasks=_db_actual[0])
```

---

## 九、开发约定

### 9.1 数据源规则

- Goals/Projects/Tasks: **DB 是唯一真实数据源**，所有操作直接查/写 DB
- Agent: 内存 registry + DB 双写，心跳时校准
- 禁止创建独立内存缓存作为主数据源

### 9.2 数据库路径

```
DB_PATH: D:\work\research\agents-nexus\data\reins.db
DATABASE_URL: sqlite:///D:/work/research/agents-nexus/data/reins.db
```

### 9.3 端口约定

| 服务 | 端口 | 说明 |
|------|------|------|
| Nexus Server | 8094 | 后端 API |
| Vite Dev Server | 5173 | 前端 |


---

## Agent Worker 设计

# Agent Worker 设计方案

> **日期**: 2026-05-01
> **目标**: 让 OpenClaw Agent 有后台进程，能从 Nexus 持续领任务、执行、上报结果

---

## 一、问题诊断

当前状况：

```
Nexus 调度器 ✅ 在跑
  → 分配任务给 guzi
  → 任务状态 in_progress
  → 没有人来真正执行 ❌
  → 永远卡在 in_progress
```

原因：OpenClaw Agent（刚子/谷子/麻子/蚊子/扣子）没有后台 worker 进程持续从 Nexus 领任务。

---

## 二、架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────┐
│ OpenClaw Agent Workspace (刚子/谷子/麻子/蚊子/扣子)    │
│                                                      │
│  agent_worker.py  ← 后台常驻进程                       │
│    while True:                                      │
│      1. heartbeat → Nexus                           │
│      2. if assigned_tasks:                          │
│           for task in assigned_tasks:               │
│             a. spawn sub-agent (sessions_spawn)      │
│             b. execute task                        │
│             c. report result (complete API)          │
│      3. sleep(30)                                  │
└──────────────────────────────────────────────────────┘
            ↕ HTTP
┌──────────────────────────────────────────────────────┐
│ Nexus (localhost:8090)                              │
│  /api/v1/agents/{id}/heartbeat → 返回 assigned_tasks │
│  /api/v1/tasks/{id}/complete  → 完成任务            │
└──────────────────────────────────────────────────────┘
```

### 2.2 Worker 流程

```
START
  ↓
注册/连接 Nexus（已有，无需改动）
  ↓
主循环 while True:
  ├─ 发送心跳 ────────────────────────────────────
  │   POST /api/v1/agents/{agent_id}/heartbeat
  │   Body: {status: "online", load: N, current_tasks: M}
  │
  ├─ 解析 assigned_tasks ──────────────────────────
  │   如果 assigned_tasks 非空：
  │     对于每个任务：
  │       a. 调用 /tasks/{id}/progress (in_progress)
  │       b. 执行任务代码（spawn sub-agent）
  │       c. 调用 /tasks/{id}/complete (done/failed)
  │
  └─ sleep(30) 后继续循环 ─────────────────────────
```

---

## 三、Worker 实现方案

### 3.1 文件位置

**文件**: `scripts/agent_worker.py`（放在 Nexus 项目 scripts 目录）

这个 worker 是 Nexus 的一部分，每个 OpenClaw Agent 运行一个 worker 实例。

### 3.2 核心代码

```python
#!/usr/bin/env python3
"""
Nexus Agent Worker

每个 OpenClaw Agent 运行一个实例，持续从 Nexus 领任务、执行、上报。

使用方式:
    python agent_worker.py <agent_id> [Nexus URL]

示例:
    python agent_worker.py guzi http://localhost:8090
    python agent_worker.py kouzi http://localhost:8090
"""

import requests
import time
import uuid
import json
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class AgentWorker:
    """Agent Worker：心跳 → 领任务 → 执行 → 上报"""

    HEARTBEAT_INTERVAL = 30  # 秒
    TASK_TIMEOUT = 600       # 任务执行超时（秒）

    def __init__(self, agent_id: str, nexus_url: str = "http://localhost:8090"):
        self.agent_id = agent_id
        self.nexus_url = nexus_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.running = True

    def heartbeat(self) -> dict:
        """
        发送心跳到 Nexus

        返回：
        {
            "success": True,
            "assigned_tasks": [...],
            "assigned_tasks_count": N,
            "load_limit_warning": False
        }
        """
        try:
            url = f"{self.nexus_url}/api/v1/agents/{self.agent_id}/heartbeat"
            payload = {
                "status": "online",
                "load": 50,
                "current_tasks": 0,
                "capabilities": ["coding", "backend", "api", "frontend", "database"],
            }
            resp = self.session.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Heartbeat failed: {resp.status_code} {resp.text[:100]}")
                return {"success": False, "assigned_tasks": []}
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return {"success": False, "assigned_tasks": []}

    def report_progress(self, task_id: str, progress: int = 50) -> bool:
        """报告任务进度"""
        try:
            url = f"{self.nexus_url}/api/v1/tasks/{task_id}/progress"
            payload = {
                "progress": progress,
                "message": f"Agent {self.agent_id} 正在执行...",
            }
            resp = self.session.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Report progress error: {e}")
            return False

    def complete_task(self, task_id: str, result: str, success: bool = True) -> bool:
        """
        完成任务上报

        参数：
        - task_id: 任务 ID
        - result: 执行结果（至少 5 字符）
        - success: 是否成功
        """
        try:
            url = f"{self.nexus_url}/api/v1/tasks/{task_id}/complete"
            payload = {
                "status": "done" if success else "failed",
                "result": result,
                "execution_log": {
                    "agent_id": self.agent_id,
                    "started_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "success": success,
                },
                "duration_ms": 1000,  # TODO: 实际执行时间
            }
            resp = self.session.post(url, json=payload, timeout=15)
            if resp.status_code in (200, 201):
                logger.info(f"Task {task_id} completed successfully")
                return True
            else:
                logger.error(f"Complete failed: {resp.status_code} {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Complete task error: {e}")
            return False

    def execute_task(self, task: dict) -> tuple[bool, str]:
        """
        执行单个任务

        目前是模拟执行（打印任务信息）。
        Phase 2 可扩展：真正 spawn OpenClaw sub-agent 来执行。

        返回：(success, result_message)
        """
        task_id = task.get("id", "?")
        title = task.get("title", "?")
        description = task.get("description", "")[:200]
        priority = task.get("priority", "medium")

        logger.info(f"[{task_id}] Executing: {title}")
        logger.info(f"[{task_id}] Priority: {priority}")
        logger.info(f"[{task_id}] Description: {description}")

        # TODO: 真正执行逻辑
        # 选项 A: spawn OpenClaw sub-agent (sessions_spawn)
        # 选项 B: 直接写代码/调用 API
        # 选项 C: 调用 LLM 生成结果

        # 模拟执行：等待一段时间
        time.sleep(2)

        result = (
            f"任务已完成：{title}\n"
            f"优先级：{priority}\n"
            f"执行时间：{datetime.now().isoformat()}\n"
            f"执行者：{self.agent_id}\n"
            f"说明：{description}"
        )
        return True, result

    def run(self):
        """
        主循环：心跳 → 领任务 → 执行 → 上报
        """
        logger.info(f"[Worker] {self.agent_id} starting...")
        logger.info(f"[Worker] Nexus: {self.nexus_url}")

        while self.running:
            try:
                # Step 1: 发送心跳
                result = self.heartbeat()

                if result.get("success"):
                    assigned_tasks = result.get("assigned_tasks", [])
                    if assigned_tasks:
                        logger.info(f"[Worker] Received {len(assigned_tasks)} tasks")
                        for task in assigned_tasks:
                            task_id = task.get("id", "?")
                            title = task.get("title", "?")

                            # 报告进度
                            self.report_progress(task_id, 10)

                            # 执行任务
                            success, result_msg = self.execute_task(task)

                            # 完成上报
                            self.complete_task(task_id, result_msg, success)
                    else:
                        logger.debug(f"[Worker] No tasks assigned")
                else:
                    logger.warning(f"[Worker] Heartbeat returned success=False")

            except KeyboardInterrupt:
                logger.info(f"[Worker] Interrupted, stopping...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"[Worker] Loop error: {e}")

            # 等待下一次心跳
            time.sleep(self.HEARTBEAT_INTERVAL)

        logger.info(f"[Worker] {self.agent_id} stopped")


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent_worker.py <agent_id> [nexus_url]")
        print("Example: python agent_worker.py guzi http://localhost:8090")
        sys.exit(1)

    agent_id = sys.argv[1]
    nexus_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8090"

    worker = AgentWorker(agent_id, nexus_url)
    worker.run()


if __name__ == "__main__":
    main()
```

### 3.3 启动方式

```bash
# 启动谷子的 worker
python scripts/agent_worker.py guzi

# 启动扣子的 worker
python scripts/agent_worker.py kouzi

# 后台运行（Windows）
start /b python scripts/agent_worker.py guzi

# 后台运行（Linux/macOS）
nohup python scripts/agent_worker.py guzi > worker_guzi.log 2>&1 &
```

### 3.4 Windows 服务化（可选 later）

用 NSSM 或 Windows Service 把 worker 注册为 Windows 服务，开机自启。

---

## 四、执行验证计划

### 4.1 验证步骤

**Step 1**: 启动谷子的 worker
```bash
python scripts/agent_worker.py guzi
```

**Step 2**: 观察日志输出
```
2026-05-01 06:50:00 [INFO] [Worker] guzi starting...
2026-05-01 06:50:00 [INFO] [Worker] Nexus: http://localhost:8090
2026-05-01 06:50:00 [INFO] [Worker] Received N tasks  ← 看到任务分配
2026-05-01 06:50:01 [INFO] [task-xxx] Executing: Task 1: scenario_task_templates...
2026-05-01 06:50:03 [INFO] [Worker] Task task-xxx completed successfully
```

**Step 3**: 验证 Nexus 任务状态
```
GET /api/v1/tasks?goal_id=goal-4440be44e1a9
→ status = "done" for completed tasks
```

### 4.2 预期结果

| 任务 | 状态变化 |
|------|---------|
| Task 1: scenario_task_templates 表 | in_progress → done |
| Task 2: source 枚举扩展 | in_progress → done |
| Task 3: 从目标提炼场景 API | in_progress → done |
| Task 4: 从项目提炼场景 API | in_progress → done |
| Task 5: 自定义场景创建 API | todo → in_progress → done |

---

## 五、后续扩展方向

### Phase 2: 真正的代码执行

目前 worker 只有模拟执行（sleep + 日志）。Phase 2 可以：

1. **方案 A: OpenClaw sessions_spawn**
   - worker 收到任务后，调用 OpenClaw API
   - spawn 一个 sub-agent 执行具体代码任务
   - 等待 sub-agent 完成，获取结果
   - 上报结果给 Nexus

2. **方案 B: 直接操作代码**
   - 读取任务描述
   - 构造 prompt 给 LLM
   - LLM 生成代码
   - 执行 shell 命令验证
   - 上报结果

### Phase 3: 多 worker 协调

- 多个 worker 同时运行（guzi + kouzi + mazi）
- 按能力分配任务（coding → kouzi, writing → wenzi）
- 避免重复分配（用 Redis 或文件锁）

---

## 六、与 Nexus 调度器的关系

```
┌─────────────────────────────────────────────────────┐
│ Nexus 调度器（后台持续运行）                          │
│                                                     │
│  每 30 秒 tick:                                    │
│    1. 健康度扫描（guzi 心跳正常）                    │
│    2. 超时回收（卡住的任务回收重分配）               │
│    3. 任务分配（guzi 有空就分新任务）               │
│    4. 调度统计（记录到 scheduler_log）              │
└──────────────────────┬──────────────────────────────┘
                       │ assigned_tasks
                       ↓
┌─────────────────────────────────────────────────────┐
│ Agent Worker（guzi 后台进程）                        │
│                                                     │
│  while True:                                       │
│    heartbeat() → 收到任务                           │
│    for task in assigned_tasks:                      │
│      execute(task) → spawn sub-agent               │
│      complete(task_id, result)                     │
│    sleep(30)                                      │
└─────────────────────────────────────────────────────┘
```

---

## 七、验收标准

1. [ ] `agent_worker.py` 文件创建在 `scripts/` 目录
2. [ ] 运行 `python agent_worker.py guzi` 无报错
3. [ ] 看到日志输出 `Received N tasks`
4. [ ] Nexus 任务状态从 `in_progress` 变为 `done`
5. [ ] 调度统计 `this_tick.assigned` > 0
6. [ ] `scheduler_log` 表有分配记录

---

*设计完成 — 2026-05-01*
