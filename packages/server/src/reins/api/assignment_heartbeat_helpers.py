"""Heartbeat helper functions — split from assignment_heartbeat.py"""

import uuid
from loguru import logger
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

def _record_error(db: Session, agent_id: str, action: str, inp: str, out: str,
                  status: str, dur_ms: int, err_msg: str):
    try:
        db.execute(sa_text("""
            INSERT INTO execution_logs (id, task_id, agent_id, action, input, output, status,
                duration_ms, created_at, error_message, result_summary, metadata,
                connectivity_verified, connectivity_check_duration_ms, skipped_reason)
            VALUES (:id, :task_id, :agent_id, :action, :input, :output, :status,
                :duration_ms, :created_at, :error_message, :result_summary, :metadata,
                :connectivity_verified, :connectivity_check_duration_ms, :skipped_reason)
        """), {
            "id": str(uuid.uuid4()), "task_id": 0, "agent_id": agent_id, "action": action,
            "input": inp, "output": out, "status": status, "duration_ms": dur_ms,
            "created_at": datetime.now(), "error_message": err_msg,
            "result_summary": f"执行异常: {err_msg}", "metadata": "{}",
            "connectivity_verified": 0, "connectivity_check_duration_ms": 0, "skipped_reason": "",
        })
        db.commit()
    except Exception:
        pass

def _record_execution_log(db: Session, agent_id: str, action: str, inp: str, out: str,
                          status: str, dur_ms: int, err_msg: str, result_summary: str,
                          metadata_val: str, conn_verified: bool, conn_dur_ms: float,
                          skip_reason: str):
    try:
        db.execute(sa_text("""
            INSERT INTO execution_logs (id, task_id, agent_id, action, input, output, status,
                duration_ms, created_at, error_message, result_summary, metadata,
                connectivity_verified, connectivity_check_duration_ms, skipped_reason)
            VALUES (:id, :task_id, :agent_id, :action, :input, :output, :status,
                :duration_ms, :created_at, :error_message, :result_summary, :metadata,
                :connectivity_verified, :connectivity_check_duration_ms, :skipped_reason)
        """), {
            "id": str(uuid.uuid4()), "task_id": 0, "agent_id": agent_id, "action": action,
            "input": inp, "output": out, "status": status, "duration_ms": dur_ms,
            "created_at": datetime.now(), "error_message": err_msg,
            "result_summary": result_summary, "metadata": metadata_val,
            "connectivity_verified": 1 if conn_verified else 0,
            "connectivity_check_duration_ms": conn_dur_ms,
            "skipped_reason": skip_reason if skip_reason else "",
        })
        db.commit()
    except Exception as exec_err:
        logger.info(f"[HEARTBEAT DEBUG] finally block INSERT failed: {exec_err}")
