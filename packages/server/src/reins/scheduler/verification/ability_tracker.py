"""
能力追踪器 — AbilityTracker

记录验证智能体的历史表现，写入 verification_task_log 表，
并提供按 agent_id 聚合统计的能力。
"""

import sqlite3
import uuid
from typing import Any, Optional

# 默认数据库路径（与 database.config 保持一致，动态推导）
from pathlib import Path as _ATPath
_DEFAULT_DB_PATH = str(_ATPath(__file__).resolve().parents[6] / "data" / "reins.db")

class AbilityTracker:
    """验证智能体能力追踪器"""

    # ------------------------------------------------------------------
    # record — 写入验证结果
    # ------------------------------------------------------------------
    @staticmethod
    def record(
        agent_id: str,
        result: Any,
        task_id: Optional[str] = None,
        verifier_type: Optional[str] = None,
        input_summary: Optional[str] = None,
        output_raw: Optional[str] = None,
        duration: Optional[float] = None,
        db_session: Optional[sqlite3.Connection] = None,
    ) -> str:
        """
        记录验证结果到 verification_task_log 表。

        参数：
            agent_id:       验证智能体 ID
            result:         验证结果（True/False 表示通过/失败；
                            也可为字符串，自动映射 passed）
            task_id:        关联任务 ID
            verifier_type:  验证器类型
            input_summary:  输入摘要
            output_raw:     原始输出
            duration:       耗时（秒）
            db_session:     已有的 sqlite3 Connection；若 None 则自建连接

        返回：
            新记录的 id
        """
        # 解析 passed
        if isinstance(result, bool):
            passed = result
        elif isinstance(result, str):
            passed = result.lower() in ("true", "pass", "1", "yes")
        else:
            passed = bool(result)

        # 生成记录 ID
        log_id = str(uuid.uuid4())

        # 决定使用哪个连接
        own_conn = db_session is None
        conn: sqlite3.Connection = db_session if not own_conn else sqlite3.connect(_DEFAULT_DB_PATH)

        try:
            conn.execute(
                """
                INSERT INTO verification_task_log
                    (id, task_id, agent_id, verifier_type,
                     input_summary, output_raw, passed, message,
                     duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    task_id,
                    agent_id,
                    verifier_type,
                    input_summary,
                    output_raw,
                    1 if passed else 0,
                    str(result) if not isinstance(result, str) else result,
                    duration,
                ),
            )
            conn.commit()
        finally:
            if own_conn:
                conn.close()

        return log_id

    # ------------------------------------------------------------------
    # get_agent_stats — 聚合统计
    # ------------------------------------------------------------------
    @staticmethod
    def get_agent_stats(
        agent_id: str,
        db_session: Optional[sqlite3.Connection] = None,
    ) -> dict:
        """
        返回某验证智能体历史表现统计。

        返回：
            {
                "total": int,           # 总验证次数
                "passed": int,          # 通过次数
                "passed_rate": float,   # 通过率 (0.0~1.0)
                "avg_duration": float,  # 平均用时（秒）
            }
        """
        own_conn = db_session is None
        conn: sqlite3.Connection = db_session if not own_conn else sqlite3.connect(_DEFAULT_DB_PATH)

        try:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                              AS total,
                    SUM(CASE WHEN passed THEN 1 ELSE 0 END) AS passed,
                    AVG(CASE WHEN passed THEN 1.0 ELSE 0.0 END) AS passed_rate,
                    AVG(duration_seconds)                 AS avg_duration
                FROM verification_task_log
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()

            total = row[0] or 0
            passed = row[1] or 0
            passed_rate = row[2] or 0.0
            avg_duration = row[3] if row[3] is not None else 0.0

            return {
                "total": total,
                "passed": passed,
                "passed_rate": round(passed_rate, 4),
                "avg_duration": round(avg_duration, 4),
            }
        finally:
            if own_conn:
                conn.close()
