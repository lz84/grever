"""
同步追踪器 — ExecutionTrackerSync

职责：
1. TraceEvent — 同步追踪事件
2. ExecutionReport — 同步执行报告
3. Trace — 同步追踪对象
4. ExecutionTrackerSync — 同步追踪器（内存 + SQLite）
"""

import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from loguru import logger
from reins.common.database import DB_PATH


@dataclass
class TraceEvent:
    event_id: str
    event_type: str
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[str] = None
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
            "event_id": self.event_id, "event_type": self.event_type,
            "task_id": self.task_id, "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(), "data": self.data,
            "duration_ms": self.duration_ms, "from_state": self.from_state,
            "to_state": self.to_state, "input_data": self.input_data,
            "output_data": self.output_data, "error_message": self.error_message,
            "error_type": self.error_type,
        }


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
    error_stack: Optional[str] = None
    cpu_time_ms: int = 0
    memory_peak_mb: float = 0.0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    network_bytes: int = 0
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id, "task_id": self.task_id,
            "task_title": self.task_title, "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms, "final_state": self.final_state,
            "success": self.success, "steps": self.steps,
            "cognitions_used": self.cognitions_used,
            "context_size_bytes": self.context_size_bytes,
            "result": self.result, "error_message": self.error_message,
            "error_stack": self.error_stack, "cpu_time_ms": self.cpu_time_ms,
            "memory_peak_mb": self.memory_peak_mb,
            "io_read_bytes": self.io_read_bytes, "io_write_bytes": self.io_write_bytes,
            "network_bytes": self.network_bytes,
            "generated_at": self.generated_at.isoformat(),
        }


class Trace:
    def __init__(self, workflow_id: str, task_id: str, task_title: str):
        self.workflow_id = workflow_id
        self.task_id = task_id
        self.task_title = task_title
        self.started_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.final_state: Optional[str] = None
        self.success: Optional[bool] = None
        self.result: Optional[dict] = None
        self.error_message: Optional[str] = None
        self._events: List[TraceEvent] = []
        self._steps: List[dict] = []
        self._cognitions_used = 0
        self._context_size_bytes = 0
        self._last_step_start: Optional[datetime] = None

    @property
    def total_duration_ms(self) -> int:
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.now()
        return int((end - self.started_at).total_seconds() * 1000)

    def add_event(self, event: TraceEvent):
        self._events.append(event)
        if event.event_type in ("agent_input", "agent_output"):
            if self._last_step_start:
                step_duration = int((event.timestamp - self._last_step_start).total_seconds() * 1000)
            else:
                step_duration = event.duration_ms
            self._steps.append({
                "timestamp": event.timestamp.isoformat(),
                "action": event.data.get("action", "unknown"),
                "type": event.event_type,
                "duration_ms": step_duration,
                "agent_id": event.agent_id,
            })
            self._last_step_start = event.timestamp
        if event.event_type == "context_injected":
            self._cognitions_used = event.data.get("cognitions_count", 0)
            self._context_size_bytes = event.data.get("context_size_bytes", 0)

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


class ExecutionTrackerSync:
    def __init__(self, db_path: str = DB_PATH):
        self._traces: Dict[str, Trace] = {}
        self._reports: Dict[str, ExecutionReport] = {}
        self._db_path = db_path
        self._db_initialized = False

    def _ensure_db(self):
        if self._db_initialized:
            return
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS trace_events (
                id TEXT PRIMARY KEY, event_type TEXT NOT NULL, workflow_id TEXT NOT NULL,
                task_id TEXT NOT NULL, agent_id TEXT, timestamp DATETIME NOT NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0, data TEXT, from_state TEXT,
                to_state TEXT, input_data TEXT, output_data TEXT, error_message TEXT,
                error_type TEXT, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_trace_events_task_timestamp ON trace_events(task_id, timestamp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_trace_events_workflow_task ON trace_events(workflow_id, task_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_trace_events_agent_timestamp ON trace_events(agent_id, timestamp)")
            c.execute("""CREATE TABLE IF NOT EXISTS trace_reports (
                id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, task_id TEXT NOT NULL,
                task_title TEXT NOT NULL, started_at DATETIME NOT NULL, completed_at DATETIME,
                total_duration_ms INTEGER NOT NULL, final_state TEXT NOT NULL,
                success INTEGER NOT NULL, steps TEXT, cognitions_used INTEGER NOT NULL DEFAULT 0,
                context_size_bytes INTEGER NOT NULL DEFAULT 0, result TEXT, error_message TEXT,
                error_stack TEXT, cpu_time_ms INTEGER NOT NULL DEFAULT 0,
                memory_peak_mb REAL NOT NULL DEFAULT 0.0, io_read_bytes INTEGER NOT NULL DEFAULT 0,
                io_write_bytes INTEGER NOT NULL DEFAULT 0, network_bytes INTEGER NOT NULL DEFAULT 0,
                generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_trace_reports_task_id ON trace_reports(task_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_trace_reports_workflow_id ON trace_reports(workflow_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_trace_reports_started_at ON trace_reports(started_at)")
            conn.commit()
            conn.close()
            self._db_initialized = True
            logger.info(f"[TraceTracker] Database initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"[TraceTracker] Failed to initialize database: {e}")

    def _persist_event(self, event: TraceEvent, workflow_id: str):
        self._ensure_db()
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("""INSERT INTO trace_events (id, event_type, workflow_id, task_id, agent_id,
                timestamp, duration_ms, data, from_state, to_state, input_data, output_data,
                error_message, error_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                event.event_id, event.event_type, workflow_id, event.task_id, event.agent_id,
                event.timestamp.isoformat(), event.duration_ms,
                json.dumps(event.data) if event.data else None,
                event.from_state, event.to_state,
                json.dumps(event.input_data) if event.input_data else None,
                json.dumps(event.output_data) if event.output_data else None,
                event.error_message, event.error_type,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[TraceTracker] Failed to persist event: {e}")

    def _persist_report(self, report: ExecutionReport):
        self._ensure_db()
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("""INSERT INTO trace_reports (id, workflow_id, task_id, task_title,
                started_at, completed_at, total_duration_ms, final_state, success, steps,
                cognitions_used, context_size_bytes, result, error_message, error_stack,
                cpu_time_ms, memory_peak_mb, io_read_bytes, io_write_bytes, network_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                f"rpt-{uuid.uuid4().hex[:8]}", report.workflow_id, report.task_id,
                report.task_title, report.started_at.isoformat(),
                report.completed_at.isoformat() if report.completed_at else None,
                report.total_duration_ms, report.final_state,
                1 if report.success else 0,
                json.dumps(report.steps) if report.steps else None,
                report.cognitions_used, report.context_size_bytes,
                json.dumps(report.result) if report.result else None,
                report.error_message, report.error_stack,
                report.cpu_time_ms, report.memory_peak_mb,
                report.io_read_bytes, report.io_write_bytes, report.network_bytes,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[TraceTracker] Failed to persist report: {e}")

    def start_trace(self, workflow_id: str, task_id: str, task_title: str,
                    agent_id: Optional[str] = None) -> Trace:
        trace = Trace(workflow_id, task_id, task_title)
        self._traces[task_id] = trace
        event = TraceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}", event_type="task_started",
            task_id=task_id, agent_id=agent_id, data={"workflow_id": workflow_id},
        )
        trace.add_event(event)
        self._persist_event(event, workflow_id)
        return trace

    def complete_trace(self, task_id: str, final_state: str, success: bool,
                       result: Optional[dict] = None, error_message: Optional[str] = None,
                       cognitions_used: int = 0, context_size_bytes: int = 0,
                       steps: Optional[List[dict]] = None, error_stack: Optional[str] = None,
                       cpu_time_ms: int = 0, memory_peak_mb: float = 0.0,
                       io_read_bytes: int = 0, io_write_bytes: int = 0,
                       network_bytes: int = 0) -> ExecutionReport:
        if task_id not in self._traces:
            return None
        trace = self._traces[task_id]
        trace.completed_at = datetime.now()
        trace.final_state = final_state
        trace.success = success
        trace.result = result
        trace.error_message = error_message
        event = TraceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            event_type="task_completed" if success else "task_failed",
            task_id=task_id, data={"final_state": final_state, "success": success},
            duration_ms=trace.total_duration_ms,
        )
        if error_message:
            event.error_message = error_message
        trace.add_event(event)
        self._persist_event(event, trace.workflow_id)
        report = ExecutionReport(
            workflow_id=trace.workflow_id, task_id=task_id, task_title=trace.task_title,
            started_at=trace.started_at, completed_at=trace.completed_at,
            total_duration_ms=trace.total_duration_ms, final_state=final_state,
            success=success, steps=steps or trace._steps,
            cognitions_used=cognitions_used, context_size_bytes=context_size_bytes,
            result=result, error_message=error_message,
            error_stack=error_stack, cpu_time_ms=cpu_time_ms,
            memory_peak_mb=memory_peak_mb, io_read_bytes=io_read_bytes,
            io_write_bytes=io_write_bytes, network_bytes=network_bytes,
        )
        self._reports[task_id] = report
        self._persist_report(report)
        del self._traces[task_id]
        return report

    def record_state_change(self, task_id: str, from_state: str, to_state: str,
                            reason: str = "", agent_id: Optional[str] = None):
        if task_id not in self._traces:
            return
        trace = self._traces[task_id]
        event = TraceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}", event_type="state_changed",
            task_id=task_id, agent_id=agent_id, data={"reason": reason},
            from_state=from_state, to_state=to_state,
        )
        trace.add_event(event)
        self._persist_event(event, trace.workflow_id)

    def record_agent_input(self, task_id: str, action: str,
                           input_data: Optional[dict] = None,
                           output_data: Optional[dict] = None,
                           status: str = "success", duration_ms: int = 0,
                           agent_id: Optional[str] = None):
        if task_id not in self._traces:
            return
        trace = self._traces[task_id]
        event = TraceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}", event_type="agent_input",
            task_id=task_id, agent_id=agent_id,
            data={"action": action, "status": status}, duration_ms=duration_ms,
            input_data=input_data, output_data=output_data,
        )
        trace.add_event(event)
        self._persist_event(event, trace.workflow_id)

    def record_context_injection(self, task_id: str, cognitions_count: int,
                                 context_size_bytes: int, retrieval_time_ms: float,
                                 agent_id: Optional[str] = None):
        if task_id not in self._traces:
            return
        trace = self._traces[task_id]
        event = TraceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}", event_type="context_injected",
            task_id=task_id, agent_id=agent_id,
            data={"cognitions_count": cognitions_count,
                  "context_size_bytes": context_size_bytes,
                  "retrieval_time_ms": retrieval_time_ms},
        )
        trace.add_event(event)
        self._persist_event(event, trace.workflow_id)

    def record_error(self, task_id: str, error_type: str, error_message: str,
                     agent_id: Optional[str] = None):
        if task_id not in self._traces:
            return
        trace = self._traces[task_id]
        event = TraceEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}", event_type="error",
            task_id=task_id, agent_id=agent_id, data={},
            error_type=error_type, error_message=error_message,
        )
        trace.add_event(event)
        self._persist_event(event, trace.workflow_id)

    def get_trace(self, task_id: str) -> Optional[Trace]:
        return self._traces.get(task_id)

    def get_report(self, task_id: str) -> Optional[ExecutionReport]:
        return self._reports.get(task_id)

    def list_traces(self) -> List[Trace]:
        return list(self._traces.values())

    def list_reports(self) -> List[ExecutionReport]:
        return list(self._reports.values())

    def _db_query(self, query: str, params: tuple = ()):
        self._ensure_db()
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_trace_events(self, task_id: str) -> List[TraceEvent]:
        try:
            rows = self._db_query("SELECT * FROM trace_events WHERE task_id = ? ORDER BY timestamp ASC", (task_id,))
            events = []
            for row in rows:
                events.append(TraceEvent(
                    event_id=row['id'], event_type=row['event_type'],
                    task_id=row['task_id'], agent_id=row['agent_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    duration_ms=row['duration_ms'],
                    data=json.loads(row['data']) if row['data'] else {},
                    from_state=row['from_state'], to_state=row['to_state'],
                    input_data=json.loads(row['input_data']) if row['input_data'] else None,
                    output_data=json.loads(row['output_data']) if row['output_data'] else None,
                    error_message=row['error_message'], error_type=row['error_type'],
                ))
            return events
        except Exception as e:
            logger.error(f"[TraceTracker] Failed to get trace events: {e}")
            return []

    def get_trace_report(self, task_id: str) -> Optional[ExecutionReport]:
        try:
            rows = self._db_query(
                "SELECT * FROM trace_reports WHERE task_id = ? ORDER BY started_at DESC LIMIT 1",
                (task_id,))
            if not rows:
                return None
            row = rows[0]
            return ExecutionReport(
                workflow_id=row['workflow_id'], task_id=row['task_id'],
                task_title=row['task_title'],
                started_at=datetime.fromisoformat(row['started_at']),
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                total_duration_ms=row['total_duration_ms'], final_state=row['final_state'],
                success=bool(row['success']),
                steps=json.loads(row['steps']) if row['steps'] else [],
                cognitions_used=row['cognitions_used'],
                context_size_bytes=row['context_size_bytes'],
                result=json.loads(row['result']) if row['result'] else None,
                error_message=row['error_message'], error_stack=row['error_stack'],
                cpu_time_ms=row['cpu_time_ms'], memory_peak_mb=row['memory_peak_mb'],
                io_read_bytes=row['io_read_bytes'], io_write_bytes=row['io_write_bytes'],
                network_bytes=row['network_bytes'],
            )
        except Exception as e:
            logger.error(f"[TraceTracker] Failed to get trace report: {e}")
            return None

    def list_reports_from_db(self, workflow_id: Optional[str] = None, limit: int = 50) -> List[ExecutionReport]:
        try:
            if workflow_id:
                rows = self._db_query(
                    "SELECT * FROM trace_reports WHERE workflow_id = ? ORDER BY started_at DESC LIMIT ?",
                    (workflow_id, limit))
            else:
                rows = self._db_query(
                    "SELECT * FROM trace_reports ORDER BY started_at DESC LIMIT ?", (limit,))
            reports = []
            for row in rows:
                reports.append(ExecutionReport(
                    workflow_id=row['workflow_id'], task_id=row['task_id'],
                    task_title=row['task_title'],
                    started_at=datetime.fromisoformat(row['started_at']),
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    total_duration_ms=row['total_duration_ms'], final_state=row['final_state'],
                    success=bool(row['success']),
                    steps=json.loads(row['steps']) if row['steps'] else [],
                    cognitions_used=row['cognitions_used'],
                    context_size_bytes=row['context_size_bytes'],
                    result=json.loads(row['result']) if row['result'] else None,
                    error_message=row['error_message'], error_stack=row['error_stack'],
                    cpu_time_ms=row['cpu_time_ms'], memory_peak_mb=row['memory_peak_mb'],
                    io_read_bytes=row['io_read_bytes'], io_write_bytes=row['io_write_bytes'],
                    network_bytes=row['network_bytes'],
                ))
            return reports
        except Exception as e:
            logger.error(f"[TraceTracker] Failed to list reports from db: {e}")
            return []
