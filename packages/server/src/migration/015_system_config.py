"""
迁移脚本 015：创建 system_config 表 + 预置配置数据

此脚本将：
1. 创建 system_config 表（统一系统配置存储）
2. 插入预置配置数据（根智能体、OpenClaw集成、系统参数）
"""

import sqlite3
import os
from pathlib import Path


def migrate():
    """执行数据库迁移"""
    db_path = Path("D:/work/research/agents-nexus/data/reins.db")

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 1. 创建 system_config 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TEXT,
                updated_by TEXT,
                UNIQUE(category, key)
            )
        """)
        print("✅ system_config 表创建成功")

        # 2. 预置配置数据
        seed_data = [
            # 根智能体配置
            ('cfg-root-001', 'root_agent', 'model', '"minimax/MiniMax-M2.7-highspeed"', '根智能体模型'),
            ('cfg-root-002', 'root_agent', 'dispatch_strategy', '"capability_match"', '调度策略'),
            ('cfg-root-003', 'root_agent', 'heartbeat_interval', '300', '心跳间隔(秒)'),
            ('cfg-root-004', 'root_agent', 'task_timeout_min', '30', '任务超时(分钟)'),
            ('cfg-root-005', 'root_agent', 'max_retries', '3', '最大重试次数'),
            ('cfg-root-006', 'root_agent', 'auto_dispatch', 'true', '自动派发'),
            ('cfg-root-007', 'root_agent', 'scheduler_tick_sec', '30', '调度器tick间隔(秒)'),
            ('cfg-root-008', 'root_agent', 'agent_id', '"fefd19b0-7c1a-4927-b294-c795c76afb9f"', '根智能体ID'),
            # OpenClaw 集成配置
            ('cfg-oc-001', 'openclaw', 'gateway_url', '"http://127.0.0.1:8080"', 'OpenClaw网关地址'),
            ('cfg-oc-002', 'openclaw', 'api_token', '""', 'OpenClaw API Token'),
            ('cfg-oc-003', 'openclaw', 'session_mapping', '"goal_per_session"', 'Session映射策略'),
            ('cfg-oc-004', 'openclaw', 'reconnect_timeout_sec', '60', '超时重连(秒)'),
            # 系统参数
            ('cfg-sys-001', 'system', 'log_level', '"INFO"', '日志级别'),
            ('cfg-sys-002', 'system', 'data_retention_days', '30', '数据保留天数'),
            ('cfg-sys-003', 'system', 'auto_cleanup_zombie', 'true', '自动清理僵尸任务'),
            ('cfg-sys-004', 'system', 'offline_threshold_min', '5', '离线阈值(分钟)'),
            ('cfg-sys-005', 'system', 'task_recover_threshold_min', '15', '任务回收阈值(分钟)'),
            ('cfg-sys-006', 'system', 'backend_port', '8094', '后端端口'),
            ('cfg-sys-007', 'system', 'frontend_port', '5173', '前端端口'),
            ('cfg-sys-008', 'system', 'task_priority', 'true', '任务调度优先级'),
            # 安全配置
            ('cfg-sec-001', 'security', 'api_auth_enabled', 'false', '启用API Token认证'),
            ('cfg-sec-002', 'security', 'cors_origins', '["http://localhost:5173"]', 'CORS允许来源'),
        ]

        inserted = 0
        skipped = 0
        for item in seed_data:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO system_config (id, category, key, value, description) VALUES (?, ?, ?, ?, ?)",
                    item
                )
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ⚠️  跳过 {item[0]}: {e}")
                skipped += 1

        print(f"✅ 预置数据: 插入 {inserted} 条, 跳过 {skipped} 条 (已存在)")

        conn.commit()
        print("✅ 数据库迁移 015 完成")
        return True

    except Exception as e:
        print(f"❌ 迁移过程中出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
