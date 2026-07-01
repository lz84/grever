"""Grever 统一日志 Schema — trace_id 跨模块透传"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid

@dataclass
class LogEntry:
    """统一日志条目"""
    module: str                          # scheduler|agent|execution|matching|...
    event_type: str                      # task_assigned|agent_heartbeat|verification_passed|...
    level: str = 'info'                  # debug|info|warn|error|critical
    trace_id: str = ''                   # 跨模块追踪 ID
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ''
    timestamp: str = ''
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    goal_id: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = 'log-' + uuid.uuid4().hex[:12]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json_line(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

# 预定义事件类型
class Events:
    # Scheduler
    TASK_ASSIGNED = 'task_assigned'
    TASK_COMPLETED = 'task_completed'
    TASK_FAILED = 'task_failed'
    TASK_TIMEOUT = 'task_timeout'
    TASK_RECOVERED = 'task_recovered'
    DEPENDENCY_UNLOCKED = 'dependency_unlocked'

    # Agent
    AGENT_HEARTBEAT = 'agent_heartbeat'
    AGENT_ONLINE = 'agent_online'
    AGENT_OFFLINE = 'agent_offline'
    AGENT_STALE = 'agent_stale'

    # Execution
    EXECUTION_STARTED = 'execution_started'
    EXECUTION_FINISHED = 'execution_finished'
    EXECUTION_ERROR = 'execution_error'

    # Verification
    VERIFICATION_STARTED = 'verification_started'
    VERIFICATION_PASSED = 'verification_passed'
    VERIFICATION_FAILED = 'verification_failed'
    VERIFICATION_DISPUTED = 'verification_disputed'

    # Matching
    MATCH_ATTEMPTED = 'match_attempted'
    MATCH_SUCCESS = 'match_success'
    MATCH_FAILED = 'match_failed'

    # HITL
    HITL_TRIGGERED = 'hitl_triggered'
    HITL_APPROVED = 'hitl_approved'
    HITL_REJECTED = 'hitl_rejected'

    # Goal/Project
    GOAL_DECOMPOSED = 'goal_decomposed'
    PROJECT_COMPLETED = 'project_completed'
    GOAL_COMPLETED = 'goal_completed'

    # Command Bus
    COMMAND_DISPATCHED = 'command_dispatched'
    COMMAND_FAILED = 'command_failed'

    # Scenario
    SCENARIO_INSTANTIATED = 'scenario_instantiated'
    SCENARIO_EVOLVED = 'scenario_evolved'
