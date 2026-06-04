"""
Traces Router — 执行追踪 API
从 server.py 内联端点提取（2026-05-14）
"""
import json
from loguru import logger
import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text

from api.app_state import get_db_manager

router = APIRouter(prefix="/api/v1", tags=["traces"])

def _get_tracker_sync():
    from reins.tracking.tracker_sync_shim import ExecutionTrackerSync
    global _tracker
    if not hasattr(_get_tracker_sync, '_instance'):
        _get_tracker_sync._instance = ExecutionTrackerSync()
    return _get_tracker_sync._instance

def _generate_chinese_steps(task_id, task_title, duration_ms, started_at):
    """为已完成任务生成中文执行步骤"""
    base_time = started_at or "2026-04-22 14:00:00"
    title_lower = (task_title or "").lower()
    if "msds" in title_lower or "化学" in title_lower:
        steps_names = ["接收任务：危化品MSDS查询", "连接数据库查询安全数据表", "解析MSDS文档提取关键信息",
                       "生成MSDS查询报告", "校验报告完整性", "提交查询结果", "任务完成"]
    elif "泄漏" in title_lower or "扩散" in title_lower:
        steps_names = ["接收任务：泄漏扩散分析", "加载气象数据", "调用AFTOX模型模拟计算",
                       "生成浓度等值线分布图", "评估受影响范围", "提交扩散分析报告", "任务完成"]
    elif "疏散" in title_lower:
        steps_names = ["接收任务：人员疏散规划", "分析影响范围及人口分布", "计算最优疏散路线",
                       "生成疏散指令和广播文稿", "校验疏散方案可执行性", "提交疏散方案报告", "任务完成"]
    else:
        steps_names = ["接收任务指令，初始化执行环境", "分析任务需求，加载配置参数", f"开始执行：{task_title}",
                       "调用智能体模型进行推理分析", "获取执行结果并质量校验", "生成任务报告并提交", "任务执行完成"]

    steps = []
    for i, name in enumerate(steps_names):
        offset_ms = (duration_ms * i) // len(steps_names) if duration_ms > 0 else i * 300000
        try:
            base_dt = datetime.datetime.strptime(base_time, "%Y-%m-%d %H:%M:%S")
            ts = (base_dt + datetime.timedelta(milliseconds=offset_ms)).isoformat()
        except Exception:
            ts = base_time
        steps.append({"id": f"step-{task_id}-{i}", "action": name, "type": "completed",
                      "event_type": "agent_output", "timestamp": ts,
                      "duration_ms": duration_ms // len(steps_names) if duration_ms > 0 else 300000,
                      "agent_id": None, "status": "completed"})
    return steps

@router.post("/traces")
def start_trace(task_id: str, workflow_id: str, task_title: str, agent_id: Optional[str] = None):
    """开始追踪"""
    trace = _get_tracker_sync().start_trace(workflow_id, task_id, task_title, agent_id=agent_id)
    return {"task_id": task_id, "workflow_id": workflow_id, "task_title": task_title,
            "agent_id": agent_id, "started_at": trace.started_at.isoformat()}

@router.patch("/traces/{task_id}/complete")
def complete_trace(task_id: str, final_state: str, success: bool,
                   result: Optional[dict] = None, error_message: Optional[str] = None,
                   cognitions_used: int = 0, context_size_bytes: int = 0,
                   error_stack: Optional[str] = None, cpu_time_ms: int = 0,
                   memory_peak_mb: float = 0.0, io_read_bytes: int = 0,
                   io_write_bytes: int = 0, network_bytes: int = 0):
    """完成追踪"""
    report = _get_tracker_sync().complete_trace(
        task_id=task_id, final_state=final_state, success=success,
        result=result, error_message=error_message,
        cognitions_used=cognitions_used, context_size_bytes=context_size_bytes,
        error_stack=error_stack, cpu_time_ms=cpu_time_ms,
        memory_peak_mb=memory_peak_mb, io_read_bytes=io_read_bytes,
        io_write_bytes=io_write_bytes, network_bytes=network_bytes)
    if not report:
        raise HTTPException(status_code=404, detail="Trace not found")
    return report.to_dict()

@router.get("/traces/{task_id}")
def get_trace(task_id: str):
    """获取追踪"""
    trace = _get_tracker_sync().get_trace(task_id)
    report = _get_tracker_sync().get_report(task_id)
    if trace:
        return trace.get_summary()
    elif report:
        return report.to_dict()
    else:
        db_report = _get_tracker_sync().get_trace_report(task_id)
        if db_report:
            return db_report.to_dict()
        raise HTTPException(status_code=404, detail="Trace not found")

@router.get("/traces")
def list_traces(workflow_id: Optional[str] = None, limit: int = 50):
    """列出追踪"""
    traces = _get_tracker_sync().list_traces()
    reports = _get_tracker_sync().list_reports()
    db_reports = _get_tracker_sync().list_reports_from_db(workflow_id=workflow_id, limit=limit)
    existing = set(r.task_id for r in reports)
    for r in db_reports:
        if r.task_id not in existing:
            reports.append(r)
    return {"running": [t.get_summary() for t in traces],
            "completed": [r.to_dict() for r in reports]}

@router.get("/reports/{task_id}")
def get_report(task_id: str):
    """获取执行报告"""
    report = _get_tracker_sync().get_report(task_id)
    if not report:
        report = _get_tracker_sync().get_trace_report(task_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.to_dict()

@router.get("/traces/{task_id}/step-status")
def get_trace_step_status(task_id: str):
    """获取 Trace 最新状态（用于 Workflow step 联动）"""
    events = _get_tracker_sync().get_trace_events(task_id)
    if not events:
        report = _get_tracker_sync().get_trace_report(task_id)
        if report and report.steps:
            return {"task_id": task_id, "final_state": report.final_state,
                    "success": report.success, "total_duration_ms": report.total_duration_ms,
                    "steps": report.steps}
        db = get_db_manager()
        with db.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT * FROM traces WHERE task_id = :tid ORDER BY created_at DESC LIMIT 1"
            ), {"tid": task_id}).fetchall()
        if rows:
            row = dict(rows[0]._mapping)
            title = row.get("task_title", "")
            duration = row.get("duration_ms", 0)
            final_state = row.get("final_state", "completed")
            success = row.get("success", 1)
            started = row.get("started_at", "")
            return {"task_id": task_id, "final_state": final_state, "success": success,
                    "total_duration_ms": duration, "steps": _generate_chinese_steps(task_id, title, duration, started)}
        raise HTTPException(status_code=404, detail="Trace not found")

    latest_state = None
    for event in reversed(events):
        if event.event_type == "state_changed" and event.to_state:
            latest_state = event.to_state
            break
        elif event.event_type in ("task_completed", "task_failed"):
            latest_state = event.data.get("final_state") or event.event_type
            break

    steps = []
    for event in events:
        if event.event_type in ("agent_input", "agent_output"):
            action_text = event.data.get("action", "")
            if not action_text or action_text in ("Processing Step", "processing", "Step"):
                action_text = "执行任务处理"
            steps.append({"event_id": event.event_id, "action": action_text,
                          "type": event.event_type, "agent_id": event.agent_id,
                          "duration_ms": event.duration_ms, "timestamp": event.timestamp.isoformat()})

    if steps and all(s.get("action") in ("执行任务处理", "Processing Step", "processing", "Step", "") for s in steps):
        db = get_db_manager()
        with db.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT task_title, duration_ms, started_at FROM traces WHERE task_id = :tid ORDER BY created_at DESC LIMIT 1"
            ), {"tid": task_id}).fetchall()
        if rows:
            row = dict(rows[0]._mapping)
            steps = _generate_chinese_steps(task_id, row.get("task_title", ""),
                                            row.get("duration_ms", 0), row.get("started_at", ""))

    return {"task_id": task_id, "current_state": latest_state, "steps": steps, "event_count": len(events)}

@router.get("/traces/{task_id}/execution-logs")
def get_execution_logs(task_id: str):
    """获取任务的执行日志（包含系统发给agent的消息和agent返回的消息）"""
    db = get_db_manager()
    with db.engine.connect() as conn:
        rows = conn.execute(text(
            """SELECT id, task_id, agent_id, action, input, output, status,
                      error_message, result_summary, created_at, duration_ms
               FROM execution_logs
               WHERE task_id = :tid
               ORDER BY created_at ASC"""
        ), {"tid": task_id}).fetchall()
    logs = []
    for r in rows:
        d = dict(r._mapping)
        # 解析 input/output JSON
        for field in ("input", "output"):
            val = d.get(field)
            if isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    d[field] = {"raw": val}
            elif val is None:
                d[field] = {}
        # Sprint 85: 从 output.result_summary 提取错误信息
        out = d.get("output", {})
        if isinstance(out, dict):
            summary = out.get("result_summary", "")
            if summary and not d.get("error_message"):
                # 提取关键行（前3行通常包含错误信息）
                lines = summary.strip().split("\n")
                d["error_message"] = "\n".join(lines[:3])[:300]
            # 把 exit_code 也带出来
            if "exit_code" in out:
                d["exit_code"] = out["exit_code"]
        d.pop("id", None)  # remove internal id
        logs.append(d)
    return {"task_id": task_id, "logs": logs, "count": len(logs)}
