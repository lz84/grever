"""
核心追踪 — 异步执行追踪器

职责：
1. TrackerEventType — 事件类型枚举
2. TrackerEvent — 追踪事件
3. ExecutionReport — 执行报告
4. Trace — 追踪对象
5. ExecutionTracker — 异步追踪器
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from loguru import logger
from shared.database.pool import get_pool


class TrackerEventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    STATE_CHANGED = "state_changed"
    AGENT_INPUT = "agent_input"
    AGENT_OUTPUT = "agent_output"
    CONTEXT_INJECTED = "context_injected"
    ERROR = "error"


@dataclass
class TrackerEvent:
    event_id: str
    event_type: TrackerEventType
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id, "event_type": self.event_type.value,
            "task_id": self.task_id, "timestamp": self.timestamp.isoformat(),
            "data": self.data, "duration_ms": self.duration_ms,
            "from_state": self.from_state, "to_state": self.to_state,
            "input_data": self.input_data, "output_data": self.output_data,
            "error_message": self.error_message, "error_type": self.error_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrackerEvent":
        return cls(
            event_id=data["event_id"],
            event_type=TrackerEventType(data["event_type"]),
            task_id=data["task_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data.get("data", {}),
            duration_ms=data.get("duration_ms", 0),
            from_state=data.get("from_state"), to_state=data.get("to_state"),
            input_data=data.get("input_data"), output_data=data.get("output_data"),
            error_message=data.get("error_message"), error_type=data.get("error_type"),
        )


@dataclass
class ExecutionReport:
    workflow_id: str
    task_id: str
    task_title: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    final_state: str = ""
    success: bool = False
    steps: List[dict] = field(default_factory=list)
    cognitions_used: int = 0
    context_size_bytes: int = 0
    result: Optional[dict] = None
    error_message: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id, "task_id": self.task_id,
            "task_title": self.task_title, "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms, "final_state": self.final_state,
            "success": self.success, "steps": self.steps,
            "cognitions_used": self.cognitions_used, "context_size_bytes": self.context_size_bytes,
            "result": self.result, "error_message": self.error_message,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class Trace:
    def __init__(self, workflow_id: str, task_id: str, task_title: str,
                 started_at: Optional[datetime] = None):
        self.workflow_id = workflow_id
        self.task_id = task_id
        self.task_title = task_title
        self.started_at = started_at or datetime.now()
        self.completed_at: Optional[datetime] = None
        self.final_state: Optional[str] = None
        self.success: Optional[bool] = None
        self.result: Optional[dict] = None
        self.error_message: Optional[str] = None
        self._events: List[TrackerEvent] = []
        self._event_counter = 0
        self._steps: List[dict] = []
        self._cognitions_used = 0
        self._context_size_bytes = 0

    @property
    def total_duration_ms(self) -> int:
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.now()
        return int((end - self.started_at).total_seconds() * 1000)

    @property
    def steps(self) -> List[dict]:
        return self._steps

    def add_event(self, event: TrackerEvent):
        self._events.append(event)
        self._event_counter += 1
        if event.event_type in (TrackerEventType.AGENT_INPUT, TrackerEventType.AGENT_OUTPUT):
            self._steps.append({
                "timestamp": event.timestamp.isoformat(),
                "action": event.data.get("action", "unknown"),
                "type": event.event_type.value,
                "duration_ms": event.duration_ms,
            })
        if event.event_type == TrackerEventType.CONTEXT_INJECTED:
            self._cognitions_used = event.data.get("cognitions_count", 0)
            self._context_size_bytes = event.data.get("context_size_bytes", 0)

    def get_events(self) -> List[TrackerEvent]:
        return self._events

    def get_summary(self) -> dict:
        return {
            "workflow_id": self.workflow_id, "task_id": self.task_id,
            "task_title": self.task_title,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "final_state": self.final_state, "success": self.success,
            "event_count": len(self._events), "step_count": len(self._steps),
            "cognitions_used": self._cognitions_used,
        }


class ExecutionTracker:
    def __init__(self, pool_name: str = "default"):
        self.pool_name = pool_name
        self.pool = get_pool(pool_name)
        self._running_traces: Dict[str, Trace] = {}
        self._event_listeners: List[callable] = []

    def register_listener(self, listener: callable):
        self._event_listeners.append(listener)

    def _notify_event(self, event: TrackerEvent):
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    async def start_trace(self, workflow_id: str, task_id: str, task_title: str) -> Trace:
        trace = Trace(workflow_id=workflow_id, task_id=task_id, task_title=task_title, started_at=datetime.now())
        event = TrackerEvent(
            event_id=f"evt-{trace._event_counter}", event_type=TrackerEventType.TASK_STARTED,
            task_id=task_id, data={"workflow_id": workflow_id},
        )
        trace.add_event(event)
        await self._persist_event(event)
        self._notify_event(event)
        self._running_traces[task_id] = trace
        logger.info(f"Trace started: workflow={workflow_id}, task={task_id}")
        return trace

    async def complete_trace(self, task_id: str, final_state: str, success: bool,
                            result: Optional[dict] = None, error_message: Optional[str] = None,
                            cognitions_used: int = 0, context_size_bytes: int = 0,
                            steps: Optional[List[dict]] = None) -> ExecutionReport:
        if task_id not in self._running_traces:
            logger.warning(f"Trace not found for task: {task_id}")
            return None
        trace = self._running_traces[task_id]
        trace.completed_at = datetime.now()
        trace.final_state = final_state
        trace.success = success
        trace.result = result
        trace.error_message = error_message

        event = TrackerEvent(
            event_id=f"evt-{trace._event_counter}",
            event_type=TrackerEventType.TASK_COMPLETED if success else TrackerEventType.TASK_FAILED,
            task_id=task_id, data={"final_state": final_state, "success": success},
            duration_ms=trace.total_duration_ms,
        )
        if error_message:
            event.error_message = error_message
        trace.add_event(event)
        await self._persist_event(event)
        self._notify_event(event)

        report = ExecutionReport(
            workflow_id=trace.workflow_id, task_id=task_id, task_title=trace.task_title,
            started_at=trace.started_at, completed_at=trace.completed_at,
            total_duration_ms=trace.total_duration_ms, final_state=final_state,
            success=success, steps=steps or trace.steps,
            cognitions_used=cognitions_used, context_size_bytes=context_size_bytes,
            result=result, error_message=error_message,
        )
        await self._persist_report(report)
        del self._running_traces[task_id]
        logger.info(f"Trace completed: workflow={trace.workflow_id}, task={task_id}, success={success}")
        return report

    async def record_agent_action(self, task_id: str, action: str,
                                  input_data: Optional[dict] = None,
                                  output_data: Optional[dict] = None,
                                  status: str = "success", duration_ms: int = 0):
        if task_id not in self._running_traces:
            return
        trace = self._running_traces[task_id]
        event = TrackerEvent(
            event_id=f"evt-{trace._event_counter}",
            event_type=TrackerEventType.AGENT_INPUT if input_data else TrackerEventType.AGENT_OUTPUT,
            task_id=task_id, data={"action": action, "status": status},
            duration_ms=duration_ms, input_data=input_data, output_data=output_data,
        )
        trace.add_event(event)
        await self._persist_event(event)
        self._notify_event(event)

    async def record_context_injection(self, task_id: str, cognitions_count: int,
                                       context_size_bytes: int, retrieval_time_ms: float):
        if task_id not in self._running_traces:
            return
        trace = self._running_traces[task_id]
        event = TrackerEvent(
            event_id=f"evt-{trace._event_counter}",
            event_type=TrackerEventType.CONTEXT_INJECTED, task_id=task_id,
            data={"cognitions_count": cognitions_count, "context_size_bytes": context_size_bytes,
                  "retrieval_time_ms": retrieval_time_ms},
        )
        trace.add_event(event)
        await self._persist_event(event)
        self._notify_event(event)

    async def record_state_change(self, task_id: str, from_state: str, to_state: str, reason: str = ""):
        if task_id not in self._running_traces:
            return
        trace = self._running_traces[task_id]
        event = TrackerEvent(
            event_id=f"evt-{trace._event_counter}",
            event_type=TrackerEventType.STATE_CHANGED, task_id=task_id,
            data={"reason": reason}, from_state=from_state, to_state=to_state,
        )
        trace.add_event(event)
        await self._persist_event(event)
        self._notify_event(event)

    async def record_error(self, task_id: str, error_type: str, error_message: str):
        if task_id not in self._running_traces:
            return
        trace = self._running_traces[task_id]
        event = TrackerEvent(
            event_id=f"evt-{trace._event_counter}",
            event_type=TrackerEventType.ERROR, task_id=task_id,
            data={}, error_type=error_type, error_message=error_message,
        )
        trace.add_event(event)
        await self._persist_event(event)
        self._notify_event(event)

    async def _persist_event(self, event: TrackerEvent):
        try:
            async with self.pool.connection() as conn:
                query = """INSERT INTO execution_events (event_id, event_type, task_id, timestamp, data,
                    duration_ms, from_state, to_state, input_data, output_data, error_message, error_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                await conn.execute(query, (
                    event.event_id, event.event_type.value, event.task_id,
                    event.timestamp.isoformat(), json.dumps(event.data), event.duration_ms,
                    event.from_state, event.to_state,
                    json.dumps(event.input_data) if event.input_data else None,
                    json.dumps(event.output_data) if event.output_data else None,
                    event.error_message, event.error_type,
                ))
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")

    async def _persist_report(self, report: ExecutionReport):
        try:
            async with self.pool.connection() as conn:
                query = """INSERT INTO execution_reports (workflow_id, task_id, task_title,
                    started_at, completed_at, total_duration_ms, final_state, success,
                    steps, cognitions_used, context_size_bytes, result, error_message, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                await conn.execute(query, (
                    report.workflow_id, report.task_id, report.task_title,
                    report.started_at.isoformat(),
                    report.completed_at.isoformat() if report.completed_at else None,
                    report.total_duration_ms, report.final_state, report.success,
                    json.dumps(report.steps), report.cognitions_used, report.context_size_bytes,
                    json.dumps(report.result) if report.result else None,
                    report.error_message, report.generated_at.isoformat(),
                ))
        except Exception as e:
            logger.error(f"Failed to persist report: {e}")

    async def get_trace(self, task_id: str) -> Optional[Trace]:
        return self._running_traces.get(task_id)

    async def get_report(self, task_id: str) -> Optional[ExecutionReport]:
        try:
            async with self.pool.connection() as conn:
                query = "SELECT * FROM execution_reports WHERE task_id = ?"
                row = await conn.execute(query, (task_id,))
                if row:
                    return ExecutionReport(
                        workflow_id=row["workflow_id"], task_id=row["task_id"],
                        task_title=row["task_title"],
                        started_at=datetime.fromisoformat(row["started_at"]),
                        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                        total_duration_ms=row["total_duration_ms"], final_state=row["final_state"],
                        success=row["success"] == 1,
                        steps=json.loads(row["steps"]) if row["steps"] else [],
                        cognitions_used=row["cognitions_used"],
                        context_size_bytes=row["context_size_bytes"],
                        result=json.loads(row["result"]) if row["result"] else None,
                        error_message=row["error_message"],
                    )
        except Exception as e:
            logger.error(f"Failed to get report: {e}")
        return None

    async def get_reports(self, workflow_id: str, start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[ExecutionReport]:
        reports = []
        try:
            async with self.pool.connection() as conn:
                query = "SELECT * FROM execution_reports WHERE workflow_id = ?"
                params = [workflow_id]
                if start_time:
                    query += " AND started_at >= ?"
                    params.append(start_time.isoformat())
                if end_time:
                    query += " AND started_at <= ?"
                    params.append(end_time.isoformat())
                query += " ORDER BY started_at DESC"
                rows = await conn.execute(query, params)
                for row in rows:
                    reports.append(ExecutionReport(
                        workflow_id=row["workflow_id"], task_id=row["task_id"],
                        task_title=row["task_title"],
                        started_at=datetime.fromisoformat(row["started_at"]),
                        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                        total_duration_ms=row["total_duration_ms"], final_state=row["final_state"],
                        success=row["success"] == 1,
                        steps=json.loads(row["steps"]) if row["steps"] else [],
                        cognitions_used=row["cognitions_used"],
                        context_size_bytes=row["context_size_bytes"],
                        result=json.loads(row["result"]) if row["result"] else None,
                        error_message=row["error_message"],
                    ))
        except Exception as e:
            logger.error(f"Failed to get reports: {e}")
        return reports
