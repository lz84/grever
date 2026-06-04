# Nexus Agent Skill

让 Agent 能从 Nexus 拉取任务并执行。这是 Nexus 超越 Paperclip 的核心能力。

## 功能说明

此 Skill 实现了 Agent 的任务派发与执行机制：

1. **任务拉取**：Agent heartbeat 时检查 `assigned_tasks`
2. **上下文读取**：获取任务描述、场景指南、历史记录
3. **任务执行**：Agent 自主执行任务
4. **结果上报**：成功则 `POST /tasks/{id}/complete`，失败则 `POST /tasks/{id}/fail`

## 触发方式

当 Agent 心跳（heartbeat）时自动触发，检查是否有新分配的任务。

## 执行流程

```
1. 触发检查（trigger.py）：
   - 调用 POST /api/v1/agents/{agent_id}/heartbeat
   - 解析返回的 assigned_tasks 列表

2. 任务执行（executor.py）：
   对每个任务：
   a. 读取任务上下文（GET /tasks/{id}/context）
   b. 读取场景指南（如果有）
   c. 自主执行任务
   d. 上报结果
      - 成功：POST /tasks/{id}/complete
      - 失败：POST /tasks/{id}/fail
```

## API 接口

### 1. Heartbeat API
- **端点**：`POST /api/v1/agents/{agent_id}/heartbeat`
- **功能**：更新心跳并获取分配的任务
- **返回**：
  - `assigned_tasks`: 分配给该 agent 的任务列表
  - `load_limit_warning`: 负载是否超限

### 2. 任务上下文 API
- **端点**：`GET /api/v1/tasks/{task_id}/context`
- **功能**：获取任务的详细上下文
- **返回**：
  - `scenario_guide`: 场景指南（如有）
  - `related_files`: 相关文件列表
  - `previous_attempts`: 历史执行记录
  - `goal_info`: 目标信息

### 3. 完成上报 API
- **端点**：`POST /api/v1/tasks/{task_id}/complete`
- **功能**：任务完成上报
- **请求体**：
  ```json
  {
    "status": "done",
    "result": "执行结果描述",
    "artifacts": ["相关文件列表"],
    "duration_ms": 执行耗时,
    "confidence": 0.95,
    "issues_encountered": ["遇到的问题"]
  }
  ```

### 4. 失败上报 API
- **端点**：`POST /api/v1/tasks/{task_id}/fail`
- **功能**：任务失败上报
- **请求体**：
  ```json
  {
    "error_type": "error类型",
    "error_message": "错误详情",
    "retry_count": 1,
    "max_retries": 3
  }
  ```

## 配置要求

Agent 配置中需要包含：
- `nexus_url`: Nexus 后端 API 地址
- `agent_id`: Agent 唯一标识
- `api_key`: 访问 Nexus 的 API Key（可选）

## 文件结构

```
nexus-agent/
├── SKILL.md          # Skill 说明（此文件）
├── README.md         # 使用说明
├── main.py           # 主入口（整合 trigger + executor）
├── trigger.py        # 任务拉取逻辑
├── executor.py       # 任务执行逻辑
└── requirements.txt  # Python 依赖
```

## 使用示例

```python
from nexus_agent import main_handler

# Agent heartbeat 回调
def on_heartbeat():
    result = main_handler()
    print(f"任务执行完成: {result['status']}")
```

## 依赖

- requests >= 2.31.0
- pydantic >= 2.0.0

## 参考文档

- 详细设计：`docs/08-前端详细设计/09-Agent派发与执行.md`
- 相关 Issue：MAK-227, MAK-214
