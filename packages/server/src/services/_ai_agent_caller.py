# -*- coding: utf-8 -*-
"""Agent calling methods — planning agent + OpenClaw CLI."""
import json
import os
import re
import subprocess
import uuid
from typing import Any, Dict, Optional, Tuple

from loguru import logger


def _get_db_path() -> str:
    """Get the Grever database path from environment."""
    return os.environ.get("SQLITE_PATH", "D:/work/research/agents-nexus/data/reins.db")


def _get_openclaw_cmd() -> list:
    """Get the openclaw CLI command as a list (for subprocess.run)."""
    cmd_env = os.environ.get("OPENCLAW_CMD")
    if cmd_env:
        if os.path.exists(cmd_env):
            return [cmd_env]
        return ["openclaw"]
    default_path = "C:/Users/liuzh/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs"
    if os.path.exists(default_path):
        node_path = os.environ.get("NODE_EXE", r"C:\nvm4w\nodejs\node.exe")
        if os.path.exists(node_path):
            return [node_path, default_path]
        return ["node", default_path]
    return ["openclaw"]


def _get_default_model(category: str) -> Optional[str]:
    """Get default model for interaction category."""
    model_map = {
        "planning": os.environ.get("OPENCLAW_DEFAULT_MODEL_PLANNING"),
        "self_review": os.environ.get("OPENCLAW_DEFAULT_MODEL_SELF_REVIEW"),
        "verification": os.environ.get("OPENCLAW_DEFAULT_MODEL_VERIFICATION"),
        "dispatch": os.environ.get("OPENCLAW_DEFAULT_MODEL_DISPATCH"),
        "knowledge": os.environ.get("OPENCLAW_DEFAULT_MODEL_KNOWLEDGE"),
    }
    return model_map.get(category) or os.environ.get("OPENCLAW_DEFAULT_MODEL")


def _get_goal_session_id(goal_id: str) -> Optional[str]:
    """Look up session_id from goal_sessions table."""
    import sqlite3
    try:
        conn = sqlite3.connect(_get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id FROM goal_sessions "
            "WHERE goal_id = ? AND status = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            (goal_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.warning(f"[_get_goal_session_id] Failed for goal_id={goal_id}: {e}")
        return None


def _extract_response_text(output: str) -> str:
    """Extract the main response text from OpenClaw CLI output."""
    if not output:
        return ""
    lines = output.strip().split("\n")
    skip_prefixes = [
        r"^\d{2}:\d{2}:\d{2}",
        r"^\[.*?\]",
        r"^(info|debug|warn|error)[:\s]",
        r"^openclaw",
        r"^Running",
        r"^Command",
        r"^$",
    ]
    meaningful_lines = []
    for line in lines:
        skip = False
        for prefix in skip_prefixes:
            if re.match(prefix, line.strip()):
                skip = True
                break
        if not skip:
            meaningful_lines.append(line)
    text = "\n".join(meaningful_lines).strip()
    if not text:
        text = "\n".join(lines[-10:]).strip()
    return text


def _send_to_session(session_id: str, prompt: str, timeout: int = 120) -> str:
    """Send a message to an existing OpenClaw CLI session."""
    openclaw_cmd = _get_openclaw_cmd()
    cmd = openclaw_cmd + ["sessions", "send", session_id, prompt]
    logger.info(f"[_send_to_session] Sending to session {session_id[:12]}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=os.environ.copy(),
        )
        output = result.stdout or result.stderr or ""
        response_text = _extract_response_text(output)
        logger.info(f"[_send_to_session] Got response: {len(response_text)} chars")
        return response_text
    except subprocess.TimeoutExpired:
        logger.error(f"[_send_to_session] Timeout for session {session_id[:12]}")
        return "Agent response timeout"
    except Exception as e:
        logger.error(f"[_send_to_session] Failed: {e}")
        raise RuntimeError(f"Failed to send to session: {e}")


def _spawn_session(
    prompt: str,
    model: Optional[str] = None,
    timeout: int = 180,
) -> Tuple[str, str]:
    """Run one agent turn via OpenClaw CLI. Returns (session_id, response_text)."""
    openclaw_cmd = _get_openclaw_cmd()
    cmd = openclaw_cmd + ["agent", "--message", prompt, "--agent", "main", "--json"]
    if model:
        cmd.extend(["--model", model])
    if timeout:
        cmd.extend(["--timeout", str(timeout)])
    logger.info(f"[_spawn_session] Running: {' '.join(cmd[:6])}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=os.environ.copy(),
        )
        output = result.stdout or ""
        session_id = f"agent-{uuid.uuid4().hex[:8]}"
        try:
            data = json.loads(output)
            session_id = data.get("result", {}).get("meta", {}).get("agentMeta", {}).get("sessionId", session_id)
            payloads = data.get("result", {}).get("payloads", [])
            response_text = "\n".join(p.get("text", "") for p in payloads if p.get("text"))
            if not response_text:
                response_text = data.get("result", {}).get("summary", output)
        except json.JSONDecodeError:
            response_text = output
        logger.info(f"[_spawn_session] session_id={session_id}, response_len={len(response_text)}")
        return session_id, response_text
    except subprocess.TimeoutExpired:
        logger.error(f"[_spawn_session] Timeout after {timeout}s")
        return f"timeout-{uuid.uuid4().hex[:8]}", "Agent response timeout"
    except Exception as e:
        logger.error(f"[_spawn_session] Failed: {e}")
        raise RuntimeError(f"Failed to run agent: {e}")


def call_planning_agent(
    rendered_prompt: str,
    prompt_template: Dict[str, Any],
    context: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Call Coordinator Agent via existing goal_session session_id."""
    goal_id = context.get("goal_id")
    session_id = kwargs.get("session_id")
    if not session_id and goal_id:
        session_id = _get_goal_session_id(goal_id)
    if not session_id:
        logger.info("[call_planning_agent] No session_id, falling back to openclaw agent CLI")
        return call_openclaw_cli(rendered_prompt, prompt_template.get('category', ''), prompt_template.get('id'), **kwargs)
    timeout = kwargs.get("timeout_seconds", 120)
    response_text = _send_to_session(session_id, rendered_prompt, timeout=timeout)
    return {
        "session_id": session_id,
        "prompt_sent": rendered_prompt[:500],
        "raw_response": response_text,
        "status": "completed",
    }


def call_openclaw_cli(
    rendered_prompt: str,
    category: str,
    interaction_id: str,
    **kwargs
) -> Dict[str, Any]:
    """Call Agent via OpenClaw CLI sessions_spawn."""
    model = kwargs.get("model") or _get_default_model(category)
    timeout = kwargs.get("timeout_seconds", 180)
    session_id = kwargs.get("session_id")
    if session_id:
        response_text = _send_to_session(session_id, rendered_prompt, timeout=timeout)
        return {
            "session_id": session_id,
            "prompt_sent": rendered_prompt[:500],
            "raw_response": response_text,
            "status": "completed",
        }
    else:
        session_id, response_text = _spawn_session(rendered_prompt, model=model, timeout=timeout)
        return {
            "session_id": session_id,
            "model": model,
            "prompt_sent": rendered_prompt[:500],
            "raw_response": response_text,
            "status": "completed",
        }
