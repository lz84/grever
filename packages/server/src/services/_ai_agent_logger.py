# -*- coding: utf-8 -*-
"""Interaction logging for AI agent calls."""
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict

from loguru import logger


def _get_db_path() -> str:
    """Get the Grever database path from environment."""
    return os.environ.get("SQLITE_PATH", "D:/work/research/agents-nexus/data/reins.db")


def log_interaction(
    interaction_id: str,
    version: int,
    context: Dict[str, Any],
    result: Dict[str, Any]
) -> None:
    """Log interaction to prompt_library_interaction_logs table."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_library_interaction_logs (
                id TEXT PRIMARY KEY,
                interaction_id TEXT NOT NULL,
                template_version INTEGER,
                context_json TEXT,
                result_json TEXT,
                status TEXT,
                error TEXT,
                created_at TEXT
            )
        """)
        log_id = f"log-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()
        status = "completed" if result.get("status") != "error" else "error"
        error = result.get("error") or ""
        cursor.execute(
            "INSERT INTO prompt_library_interaction_logs "
            "(id, interaction_id, template_version, context_json, result_json, "
            "status, error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, interaction_id, version,
             json.dumps(context, ensure_ascii=False)[:2000],
             json.dumps(result, ensure_ascii=False)[:4000],
             status, error[:500], now)
        )
        conn.commit()
        conn.close()
        logger.debug(f"[log_interaction] Logged {interaction_id} v{version}")
    except Exception as e:
        logger.warning(f"[log_interaction] Failed to log interaction: {e}")
