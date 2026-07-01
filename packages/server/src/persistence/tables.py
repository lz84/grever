"""
Grever Reins 数据库表定义
使用 SQLAlchemy Core，支持多数据库后端
"""

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    JSON,
    Text,
    Index,
)
from datetime import datetime

# 通用元数据
metadata = MetaData()

# ========== 目标表 (goals) ==========
goals = Table(
    "goals",
    metadata,
    Column("id", String(32), primary_key=True, comment="目标 ID"),
    Column("title", String(255), nullable=False, comment="目标标题"),
    Column("description", String(2000), comment="目标描述"),
    Column("parent_id", String(32), comment="父目标 ID"),
    Column("status", String(20), nullable=False, default="created", comment="状态"),
    Column("progress", Float, nullable=False, default=0.0, comment="进度 0-1"),
    Column("task_ids", JSON, comment="子任务 ID 列表"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Column("completed_at", DateTime, comment="完成时间"),
    Column("verifier_agent_id", String(32), comment="验证 Agent ID（三级验证机制）"),
    Index("idx_goals_status", "status"),
    Index("idx_goals_parent", "parent_id"),
)

# ========== 项目表 (projects) ==========
projects = Table(
    "projects",
    metadata,
    Column("id", String(32), primary_key=True, comment="项目 ID"),
    Column("name", String(255), nullable=False, comment="项目名称"),
    Column("description", String(2000), comment="项目描述"),
    Column("goal_id", String(32), comment="关联目标 ID"),
    Column("status", String(20), nullable=False, default="active", comment="状态"),
    Column("members", JSON, comment="成员列表"),
    Column("task_ids", JSON, comment="任务 ID 列表"),
    Column("parent_workflow_id", String(36), comment="关联的父工作流 ID"),
    Column("phase_order", Integer, nullable=False, default=0, comment="阶段顺序"),
    Column("workflow_id", String(36), comment="工作流 ID（冗余字段便于查询）"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Column("completed_at", DateTime, comment="完成时间"),
    Column("verifier_agent_id", String(32), comment="验证 Agent ID（三级验证机制）"),
    Index("idx_projects_status", "status"),
    Index("idx_projects_goal", "goal_id"),
    Index("idx_projects_parent_workflow", "parent_workflow_id"),
    Index("idx_projects_workflow", "workflow_id"),
)

# ========== 任务表 (tasks) ==========
tasks = Table(
    "tasks",
    metadata,
    Column("id", String(36), primary_key=True, comment="任务 ID (UUID)"),
    Column("title", String(255), nullable=False, comment="任务标题"),
    Column("description", String(5000), comment="任务描述"),
    Column("project_id", String(36), comment="所属项目 ID"),
    Column("goal_id", String(36), comment="所属目标 ID"),
    Column("assigned_agent", String(36), comment="分配的 Agent ID"),
    Column("status", String(20), nullable=False, default="todo", comment="状态"),
    Column("priority", Integer, nullable=False, default=1, comment="优先级"),
    Column("category", String(50), comment="任务类型"),
    Column("dependencies", JSON, comment="依赖的任务 ID 列表"),
    Column("depends_on", JSON, comment="被依赖的任务 ID 列表"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Column("started_at", DateTime, comment="开始时间"),
    Column("completed_at", DateTime, comment="完成时间"),
    Column("estimated_hours", Float, comment="预估工时"),
    Column("actual_hours", Float, comment="实际工时"),
    Column("result", String(5000), comment="执行结果"),
    Column("acceptance_criteria", String(5000), comment="验收标准（Sprint 50-52 质量问题修复）"),
    Column("delivery_criteria", String(5000), comment="交付标准（Sprint 86 执行者交付物清单）"),
    Column("verifier_agent_id", String(32), comment="验证 Agent ID（三级验证机制）"),
    Column("needs_verification", Boolean, default=True, comment="是否需要验证（Sprint 66 强制机制，默认需要）"),
    Column("verification_cycle", Integer, default=0, comment="验证循环次数（0=未验证）"),
    Index("idx_tasks_status", "status"),
    Index("idx_tasks_project", "project_id"),
    Index("idx_tasks_goal", "goal_id"),
    Index("idx_tasks_agent", "assigned_agent"),
    Index("idx_tasks_priority", "priority"),
)

# ========== Agent 注册表 (agents) ==========
agents = Table(
    "agents",
    metadata,
    Column("id", String(36), primary_key=True, comment="Agent ID (UUID)"),
    Column("name", String(255), nullable=False, comment="Agent 名称"),
    Column("capabilities", JSON, nullable=False, comment="能力列表"),
    Column("status", String(20), nullable=False, default="offline", comment="状态"),
    Column("address", String(500), comment="Agent 地址"),
    Column("metadata", JSON, comment="元数据"),
    Column("load", Integer, nullable=False, default=0, comment="负载百分比"),
    Column("current_tasks", Integer, nullable=False, default=0, comment="当前任务数"),
    # P5-05: 触发模式
    Column("trigger_mode", String(20), nullable=False, default="sse", comment="触发模式: sse/polling"),
    # P5-05: 轮询间隔（秒），仅 trigger_mode=polling 时有效
    Column("poll_interval_seconds", Integer, nullable=False, default=10, comment="轮询间隔（秒）"),
    # P5-06: 模型名称
    Column("model_name", String(255), default="", comment="使用的模型名称"),
    Column("registered_at", DateTime, nullable=False, default=datetime.now, comment="注册时间"),
    Column("last_heartbeat", DateTime, nullable=False, default=datetime.now, comment="最后心跳时间"),
    Index("idx_agents_status", "status"),
    Index("idx_agents_trigger_mode", "trigger_mode"),
)

# ========== 争议表 (disputes) ==========
disputes = Table(
    "disputes",
    metadata,
    Column("id", String(32), primary_key=True, comment="争议 ID"),
    Column("dispute_type", String(50), nullable=False, comment="争议类型"),
    Column("description", String(5000), nullable=False, comment="描述"),
    Column("involved_agents", JSON, nullable=False, comment="涉及的 Agent ID 列表"),
    Column("related_task_id", String(32), comment="关联任务 ID"),
    Column("status", String(20), nullable=False, default="open", comment="状态"),
    Column("resolution", String(5000), comment="解决方案"),
    Column("resolved_by", String(32), comment="解决者"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Column("resolved_at", DateTime, comment="解决时间"),
    Index("idx_disputes_status", "status"),
    Index("idx_disputes_task", "related_task_id"),
)

# ========== 工作流表 (workflows) ==========
workflows = Table(
    "workflows",
    metadata,
    Column("id", String(36), primary_key=True, comment="工作流 ID (UUID)"),
    Column("goal_id", String(36), comment="关联目标 ID"),
    Column("status", String(20), nullable=False, default="draft", comment="工作流状态"),
    Column("name", String(500), nullable=False, comment="工作流名称"),
    Column("description", String(5000), comment="工作流描述"),
    Column("dag", JSON, comment="DAG 结构: {nodes:[], edges:[]}"),
    Column("workflow_metadata", JSON, comment="元数据"),
    Column("created_by", String(200), comment="创建者"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Column("started_at", DateTime, comment="开始时间"),
    Column("completed_at", DateTime, comment="完成时间"),
    Index("idx_workflows_goal_id", "goal_id"),
    Index("idx_workflows_status_created", "status", "created_at"),
)

# ========== 工作流步骤表 (workflow_steps) ==========
workflow_steps = Table(
    "workflow_steps",
    metadata,
    Column("id", String(36), primary_key=True, comment="步骤 ID (UUID)"),
    Column("workflow_id", String(36), nullable=False, comment="关联工作流 ID"),
    Column("name", String(500), nullable=False, comment="步骤名称"),
    Column("description", String(5000), comment="步骤描述"),
    Column("status", String(20), nullable=False, default="pending", comment="步骤状态"),
    Column("dependencies", JSON, comment="依赖步骤 ID 列表"),
    Column("order", Integer, comment="执行顺序"),
    Column("agent_id", String(36), comment="执行 Agent ID"),
    Column("input_data", JSON, comment="输入数据"),
    Column("output_data", JSON, comment="输出数据"),
    Column("error", String(5000), comment="错误信息"),
    Column("retry_count", Integer, nullable=False, default=0, comment="重试次数"),
    Column("max_retries", Integer, nullable=False, default=3, comment="最大重试次数"),
    Column("timeout_seconds", Integer, comment="超时秒数"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Column("started_at", DateTime, comment="开始时间"),
    Column("completed_at", DateTime, comment="完成时间"),
    Index("idx_workflow_steps_workflow_id", "workflow_id"),
    Index("idx_workflow_steps_status", "status"),
    Index("idx_workflow_steps_workflow_order", "workflow_id", "order"),
)

# ========== Task Activity Log 表 (activity_log) ==========
# P5-03-07: 记录 Task 状态变更历史
task_activity_log = Table(
    "task_activity_log",
    metadata,
    Column("id", String(36), primary_key=True, comment="日志 ID (UUID)"),
    Column("task_id", String(32), nullable=False, index=True, comment="关联任务 ID"),
    Column("old_status", String(20), nullable=False, comment="原状态"),
    Column("new_status", String(20), nullable=False, comment="新状态"),
    Column("reason", String(500), comment="变更原因"),
    Column("actor", String(64), comment="触发者 (agent_id 或 user_id)"),
    Column("timestamp", DateTime, nullable=False, default=datetime.now, comment="变更时间"),
    Column("extra", JSON, comment="额外数据"),
    Index("idx_activity_task_timestamp", "task_id", "timestamp"),
)

# ========== P5-05: 心跳日志表 (heartbeat_logs) ==========
heartbeat_logs = Table(
    "heartbeat_logs",
    metadata,
    Column("id", String(36), primary_key=True, comment="日志 ID (UUID)"),
    Column("agent_id", String(32), nullable=False, index=True, comment="Agent ID"),
    Column("timestamp", DateTime, nullable=False, default=datetime.now, comment="心跳时间"),
    Column("status", String(20), nullable=False, default="online", comment="Agent 状态"),
    Column("latency_ms", Integer, comment="延迟（毫秒）"),
    Column("load", Integer, comment="当时负载"),
    Column("current_tasks", Integer, comment="当时任务数"),
    Column("extra", JSON, comment="额外数据"),
    Column("raw_payload", Text, comment="完整心跳载荷 JSON"),
    Index("idx_heartbeat_agent_timestamp", "agent_id", "timestamp"),
)

# ========== MAK-215: 任务失败日志表 (task_failure_log) ==========
task_failure_log = Table(
    "task_failure_log",
    metadata,
    Column("id", String(36), primary_key=True, comment="日志 ID (UUID)"),
    Column("task_id", String(32), nullable=False, index=True, comment="关联任务 ID"),
    Column("error_type", String(100), nullable=False, comment="错误类型"),
    Column("error_message", String(5000), comment="错误消息"),
    Column("retry_count", Integer, nullable=False, comment="重试次数"),
    Column("max_retries", Integer, nullable=False, comment="最大重试次数"),
    Column("timestamp", DateTime, nullable=False, default=datetime.now, comment="失败时间"),
    Index("idx_failure_task_timestamp", "task_id", "timestamp"),
)

# ========== 人类输入请求表 (human_input_requests) ==========
human_input_requests = Table(
    "human_input_requests",
    metadata,
    Column("id", String(36), primary_key=True, comment="人类输入请求 ID (UUID)"),
    Column("task_id", String(36), nullable=False, index=True, comment="关联任务 ID"),
    Column("title", String(255), nullable=False, comment="请求标题"),
    Column("description", String(2000), comment="请求描述"),
    Column("input_type", String(50), nullable=False, default="confirmation", comment="输入类型: confirmation/approval/data_entry/selection"),
    Column("status", String(20), nullable=False, default="pending", comment="状态: pending/submitted/rejected/cancelled"),
    Column("input_data", JSON, comment="输入数据"),
    Column("submitted_by", String(100), comment="提交者"),
    Column("submitted_at", DateTime, comment="提交时间"),
    Column("context", JSON, comment="上下文信息"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Index("idx_human_input_task", "task_id"),
    Index("idx_human_input_status", "status"),
    Index("idx_human_input_submitted", "submitted_at"),
)

# ========== P1-01: 全链路执行日志表 (execution_logs) ==========
# 全链路记录: heartbeat → task_start → task_progress → task_complete
execution_logs = Table(
    "execution_logs",
    metadata,
    Column("id", String(36), primary_key=True, comment="日志 ID (UUID)"),
    Column("task_id", String(36), nullable=True, index=True, comment="关联任务ID（heartbeat时可为NULL）"),
    Column("agent_id", String(36), nullable=False, index=True, comment="Agent ID"),
    Column("action", String(50), nullable=False, comment="动作类型: heartbeat, task_start, task_progress, task_complete"),
    Column("input", JSON, comment="输入数据"),
    Column("output", JSON, comment="输出数据"),
    Column("status", String(20), nullable=False, default="success", comment="状态: success, failure"),
    Column("duration_ms", Integer, default=0, comment="耗时（毫秒）"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("error_message", String(5000), comment="错误信息"),
    Column("result_summary", String(1000), comment="结果摘要"),
    Column("metadata", JSON, comment="额外元数据"),
    Column("connectivity_verified", Boolean, default=False, comment="连接是否验证"),
    Index("idx_execution_logs_agent_created", "agent_id", "created_at"),
    Index("idx_execution_logs_task_action", "task_id", "action"),
    Index("idx_execution_logs_action", "action"),
)

# ========== Sprint 105-3: Capsule 表 (capsules) ==========
# Evo 进化域：基因固化后的可复用记忆体
capsules = Table(
    "capsules",
    metadata,
    Column("id", String(36), primary_key=True, comment="Capsule ID"),
    Column("schema_version", Integer, nullable=False, default=1, comment="Schema 版本"),
    Column("trigger", JSON, comment="触发条件（GEP trigger）"),
    Column("gene_id", String(36), comment="来源基因 ID"),
    Column("summary", String(2000), comment="Capsule 摘要"),
    Column("confidence", Float, nullable=False, default=0.0, comment="置信度 0-1"),
    Column("blast_radius", JSON, comment="影响范围"),
    Column("outcome", JSON, comment="结果状态 {status, score, ...}"),
    Column("success_streak", Integer, nullable=False, default=0, comment="连续成功次数"),
    Column("content", String(5000), comment="Capsule 内容/模板"),
    Column("diff", String(5000), comment="差异/变更"),
    Column("strategy", JSON, comment="策略配置"),
    Column("a2a", JSON, comment="Agent-to-Agent 元数据"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Index("idx_capsules_gene", "gene_id"),
    Index("idx_capsules_created", "created_at"),
)

# ========== A2A 消息表 (a2a_messages) ==========
# Agent-to-Agent 消息传递
a2a_messages = Table(
    "a2a_messages",
    metadata,
    Column("id", String(36), primary_key=True, comment="消息 ID"),
    Column("broadcast_id", String(36), comment="广播 ID（批量消息共享）"),
    Column("source_agent_id", String(36), nullable=False, comment="源 Agent ID"),
    Column("target_agent_id", String(36), nullable=False, comment="目标 Agent ID"),
    Column("message", String(5000), nullable=False, comment="消息内容"),
    Column("channel", String(50), nullable=False, default="default", comment="频道"),
    Column("priority", String(20), nullable=False, default="normal", comment="优先级: low/normal/high/urgent"),
    Column("status", String(20), nullable=False, default="pending", comment="状态: pending/delivered/read/processed/rejected"),
    Column("metadata", JSON, comment="额外元数据"),
    Column("requires_ack", Boolean, default=False, comment="是否需要确认"),
    Column("ack_status", String(20), comment="确认状态"),
    Column("ack_response", String(5000), comment="确认响应"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("delivered_at", DateTime, comment="送达时间"),
    Column("ack_at", DateTime, comment="确认时间"),
    Index("idx_a2a_source", "source_agent_id"),
    Index("idx_a2a_target", "target_agent_id"),
    Index("idx_a2a_status", "status"),
    Index("idx_a2a_broadcast", "broadcast_id"),
    Index("idx_a2a_created", "created_at"),
)

# ========== 信任评估记录表 (trust_evaluations) ==========
# Vigil 信任域：Agent 信任评分历史
trust_evaluations = Table(
    "trust_evaluations",
    metadata,
    Column("id", String(36), primary_key=True, comment="评估 ID"),
    Column("agent_id", String(36), nullable=False, comment="Agent ID"),
    Column("score", Float, nullable=False, comment="信任评分 0-1"),
    Column("level", String(20), nullable=False, comment="信任等级: trusted/neutral/suspicious/blocked"),
    Column("reason", String(1000), comment="评估原因"),
    Column("category", String(50), comment="评估类别"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="评估时间"),
    Index("idx_trust_agent", "agent_id"),
    Index("idx_trust_created", "created_at"),
)

# ========== RBAC 角色表 (roles) ==========
# Vigil 权限域：角色定义
roles = Table(
    "roles",
    metadata,
    Column("id", String(36), primary_key=True, comment="角色 ID"),
    Column("name", String(100), nullable=False, unique=True, comment="角色名称"),
    Column("description", String(500), comment="角色描述"),
    Column("permissions", JSON, comment="权限列表"),
    Column("level", Integer, nullable=False, default=1, comment="角色等级"),
    Column("status", String(20), nullable=False, default="active", comment="状态: active/inactive"),
    Column("created_at", DateTime, nullable=False, default=datetime.now, comment="创建时间"),
    Column("updated_at", DateTime, nullable=False, default=datetime.now, comment="更新时间"),
    Index("idx_roles_status", "status"),
    Index("idx_roles_level", "level"),
)

# ========== 能力标签表 (capability_tags) ==========
# Sprint 87: Agentic Loop 自检标准来源
capability_tags = Table(
    "capability_tags",
    metadata,
    Column("id", String(36), primary_key=True, comment="标签 ID"),
    Column("name", String(100), nullable=False, unique=True, comment="标签名称"),
    Column("parent_tag", String(36), comment="父标签 ID（支持标准继承）"),
    Column("standards", JSON, default=list, comment="过程标准列表"),
    Column("created_at", Integer, comment="创建时间 Unix timestamp"),
    Column("updated_at", Integer, comment="更新时间 Unix timestamp"),
    Index("idx_cap_parent", "parent_tag"),
)
