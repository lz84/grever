"""Migration 030 Python helper: seed system_config default values."""

import os
import sqlite3
import uuid
from datetime import datetime, timezone


def seed_system_config():
    """Insert default system_config rows (INSERT OR IGNORE = idempotent)."""
    db_path = os.environ.get("SQLITE_PATH")
    if not db_path:
        # 默认使用主 DB（与 database/config.py 一致）
        db_path = r"D:\work\research\agents-nexus\data\reins.db"
    if not os.path.exists(db_path):
        print(f"[seed] DB not found at {db_path}, skipping")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if system_config table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'"
    )
    if not cursor.fetchone():
        print("[seed] system_config table not found, skipping")
        conn.close()
        return

    now = datetime.now(timezone.utc).isoformat()

    seed_data = [
        # Agent 主动探测参数
        (
            f"cfg-agent-001-{uuid.uuid4().hex[:8]}",
            "agent",
            "agent_probe_enabled",
            "true",
            "启用 Agent 主动探测（Pull 模式）",
        ),
        (
            f"cfg-agent-002-{uuid.uuid4().hex[:8]}",
            "agent",
            "agent_probe_interval_seconds",
            "300",
            "Agent 主动探测间隔（秒），默认 5 分钟",
        ),
        (
            f"cfg-agent-003-{uuid.uuid4().hex[:8]}",
            "agent",
            "agent_probe_timeout_seconds",
            "5",
            "Agent 主动探测 HTTP 超时（秒）",
        ),
        (
            f"cfg-agent-004-{uuid.uuid4().hex[:8]}",
            "agent",
            "agent_probe_path",
            "/health",
            "Agent 健康检查端点路径",
        ),
        # 根智能体配置（向后兼容）
        (
            f"cfg-root-001-{uuid.uuid4().hex[:8]}",
            "root_agent",
            "model",
            '"minimax/MiniMax-M2.7-highspeed"',
            "根智能体模型",
        ),
        (
            f"cfg-root-002-{uuid.uuid4().hex[:8]}",
            "root_agent",
            "dispatch_strategy",
            '"capability_match"',
            "调度策略",
        ),
        (
            f"cfg-root-003-{uuid.uuid4().hex[:8]}",
            "root_agent",
            "heartbeat_interval",
            "300",
            "心跳间隔(秒)",
        ),
        (
            f"cfg-root-004-{uuid.uuid4().hex[:8]}",
            "root_agent",
            "task_timeout_min",
            "30",
            "任务超时(分钟)",
        ),
        # OpenClaw 集成
        (
            f"cfg-oc-001-{uuid.uuid4().hex[:8]}",
            "openclaw",
            "gateway_url",
            '"http://127.0.0.1:8080"',
            "OpenClaw Gateway 地址",
        ),
        (
            f"cfg-oc-002-{uuid.uuid4().hex[:8]}",
            "openclaw",
            "api_token",
            '""',
            "OpenClaw API Token",
        ),
    ]

    inserted = 0
    skipped = 0
    for item_id, category, key, value, desc in seed_data:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO system_config (id, category, key, value, description) VALUES (?, ?, ?, ?, ?)",
                (item_id, category, key, value, desc),
            )
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ⚠️  跳过 {key}: {e}")
            skipped += 1

    conn.commit()
    print(f"[seed] system_config: inserted {inserted}, skipped {skipped}")
    conn.close()


if __name__ == "__main__":
    seed_system_config()
