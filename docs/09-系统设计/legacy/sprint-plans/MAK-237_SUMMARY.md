"""
MAK-237 Agent 负载管理与限流 - 实现总结

## 完成内容：

### 1. 创建 load_manager.py
- 实现了三个 API 端点：
  - GET /agents/{id}/load - 查看当前负载
  - PUT /agents/{id}/config - 更新负载配置
  - GET /agents/{id}/pending-tasks - 查看待领取任务
- 实现了 load_config 模型（max_concurrent_tasks, load_threshold, recovery_threshold）
- 实现了离线处理函数：
  - check_agent_online - 检查 Agent 是否在线（5分钟阈值）
  - reassign_tasks_for_offline_agent - 重新分配 offline Agent 的任务
  - check_and_mark_agents_offline - 标记超过 5 分钟未 heartbeat 的 Agent 为 offline

### 2. 更新数据库迁移文件
- 创建了 009_add_agent_load_config.sql 迁移文件，添加负载配置字段

### 3. 更新 assignment.py
- 在 assign_tasks_to_agent 函数中添加了负载配置支持
- 添加了 check_load_limit 参数，默认检查 Agent 的负载限制
- 更新 heartbeat API 更新 Agent 的 current_tasks 和 load

### 4. 更新 server.py
- 注册了 load_manager_router 路由
- 更新了数据库初始化代码，添加负载配置字段迁移
- 更新了 init_workflow_router 调用（db_manager -> db_mgr）

### 5. 更新 background_tasks.py
- 在 HeartbeatOfflineDetector 中添加了 db_manager 参数
- 在标记 Agent 为 offline 后，如果超过 5 分钟则重新分配其任务
- 实现了 _reassign_offline_agent_tasks 函数

## API 端点：

### GET /agents/{id}/load
返回：
```json
{
  "agent_id": "agent-001",
  "current_tasks": 5,
  "current_load": 80,
  "is_overloaded": true,
  "pending_tasks_count": 3,
  "load_threshold": 80,
  "recovery_threshold": 50
}
```

### PUT /agents/{id}/config
请求体：
```json
{
  "max_concurrent_tasks": 10,
  "load_threshold": 90,
  "recovery_threshold": 60
}
```

### GET /agents/{id}/pending-tasks
返回：
```json
{
  "agent_id": "agent-001",
  "pending_tasks": [...],
  "total_count": 5,
  "is_overloaded": true
}
```

## 离线处理：

1. 检查 Agent 最后 heartbeat 超过 5 分钟 → 标记为 offline
2. 对 offline Agent：
   - pending 任务 → assigned_agent = NULL（允许其他 Agent 领取）
   - in_progress 任务 → status = 'blocked', blocked_reason = 'Agent went offline'

## 超负载处理：

- 当前任务数 >= max_concurrent_tasks 或 当前负载 >= load_threshold → is_overloaded = true
- 分配任务时，超负载 Agent 不接收新任务
