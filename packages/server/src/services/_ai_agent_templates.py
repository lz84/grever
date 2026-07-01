# -*- coding: utf-8 -*-
"""Prompt template management for AI agent interactions."""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger


def _get_db_path() -> str:
    """Get the Grever database path from environment."""
    return os.environ.get("SQLITE_PATH", "D:/work/research/agents-nexus/data/reins.db")


def _parse_json_field(value):
    """Parse JSON field value."""
    if not value:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


_COLUMNS = ["id", "version", "content", "context_schema", "category",
            "description", "output_schema", "status"]


def get_prompt_template(interaction_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest active prompt template for interaction_id."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, version, content, context_schema, category, "
            "description, output_schema, status "
            "FROM prompt_library "
            "WHERE id = ? AND status = 'active' "
            "ORDER BY version DESC LIMIT 1",
            (interaction_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        result = dict(zip(_COLUMNS, row))
        result["context_schema"] = _parse_json_field(result["context_schema"])
        result["output_schema"] = _parse_json_field(result["output_schema"])
        return result
    except Exception as e:
        logger.error(f"[get_prompt_template] Failed for {interaction_id}: {e}")
        return None


def update_prompt_template(
    interaction_id: str,
    content: str,
    context_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a prompt template (creates new version for hot reload)."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(version), 0) FROM prompt_library WHERE id = ?",
            (interaction_id,)
        )
        max_version = cursor.fetchone()[0]
        new_version = max_version + 1
        now = datetime.utcnow().isoformat()
        context_schema_json = json.dumps(context_schema, ensure_ascii=False) if context_schema else ""
        output_schema_json = json.dumps(output_schema, ensure_ascii=False) if output_schema else ""
        cursor.execute(
            "INSERT INTO prompt_library "
            "(id, version, content, context_schema, category, description, "
            "output_schema, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
            (interaction_id, new_version, content,
             context_schema_json, category or "", description or "",
             output_schema_json, now, now)
        )
        cursor.execute(
            "UPDATE prompt_library SET status = 'deprecated' "
            "WHERE id = ? AND version < ?",
            (interaction_id, new_version)
        )
        conn.commit()
        conn.close()
        logger.info(f"[update_prompt_template] Updated {interaction_id} to v{new_version}")
        return get_prompt_template(interaction_id)
    except Exception as e:
        logger.error(f"[update_prompt_template] Failed for {interaction_id}: {e}")
        raise RuntimeError(f"Failed to update prompt template: {e}")


def list_prompt_templates(category: Optional[str] = None) -> list:
    """List all prompt templates, optionally filtered by category."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "SELECT id, version, content, context_schema, category, "
                "description, output_schema, status "
                "FROM prompt_library "
                "WHERE category = ? AND status = 'active' "
                "ORDER BY id, version DESC",
                (category,)
            )
        else:
            cursor.execute(
                "SELECT id, version, content, context_schema, category, "
                "description, output_schema, status "
                "FROM prompt_library "
                "WHERE status = 'active' "
                "ORDER BY id, version DESC"
            )
        rows = cursor.fetchall()
        conn.close()
        result = []
        seen = set()
        for row in rows:
            d = dict(zip(_COLUMNS, row))
            if d["id"] not in seen:
                seen.add(d["id"])
                d["context_schema"] = _parse_json_field(d["context_schema"])
                d["output_schema"] = _parse_json_field(d["output_schema"])
                result.append(d)
        return result
    except Exception as e:
        logger.error(f"[list_prompt_templates] Failed: {e}")
        return []
