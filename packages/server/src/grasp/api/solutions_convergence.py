from fastapi import HTTPException
from datetime import datetime
# -*- coding: utf-8 -*-
import json as _json
from loguru import logger

from fastapi import APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import text
from reins.common.database import get_db

router = APIRouter()

def _serialize(val):
    """Serialize value to JSON string"""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    import json
    return json.dumps(val, ensure_ascii=False)

def _next_round(db: Session, goal_id: str) -> int:
    """查询某 goal 下已有的最大 round + 1"""
    result = db.execute(
        text("SELECT COALESCE(MAX(round), 0) + 1 FROM solutions WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).fetchone()
    return result[0] if result else 1

def check_convergence(goal_id: str, db: Session) -> tuple[bool, str]:
    """
    判断方案是否收敛。

    收敛条件（满足任一即收敛）：
    1. 标准差收敛：所有方案评分标准差 < 0.05（方案之间差异小）
    2. 差距够大：top1/top2 评分差 > 0.5（最优方案已明显优于次优）

    参数:
        goal_id: 目标ID
        db: 数据库会话

    返回:
        (是否收敛, 收敛原因文字)
    """
    import statistics

    # 获取该 goal 下所有方案评分
    rows = db.execute(
        text("SELECT score FROM solutions WHERE goal_id = :gid AND score IS NOT NULL ORDER BY score DESC"),
        {"gid": goal_id}
    ).fetchall()

    if not rows:
        return False, "无方案数据，无法判断收敛"

    scores = [r[0] for r in rows]

    # 条件1：标准差 < 0.05
    if len(scores) >= 2:
        try:
            std_val = statistics.stdev(scores)
            std_converged = std_val < 0.05
        except statistics.StatisticsError:
            std_val = 0.0
            std_converged = True
    else:
        std_val = 0.0
        std_converged = False  # 只有一个方案时不用标准差判断

    # 条件2：top1/top2 差值 > 0.5
    gap_converged = False
    gap_reason = ""
    if len(scores) >= 2:
        top1 = scores[0]
        top2 = scores[1]
        gap = top1 - top2
        gap_converged = gap > 0.5
        gap_reason = f"top1={top1:.3f}, top2={top2:.3f}, gap={gap:.3f}"
    else:
        gap = 0.0
        gap_reason = "方案不足2个，跳过差距判断"

    if std_converged:
        return True, f"标准差收敛: std={std_val:.4f} < 0.05"
    if gap_converged:
        return True, f"差距够大: {gap_reason} (gap > 0.5)"
    return False, f"未收敛: std={std_val:.4f} (需<0.05), gap={gap:.3f} (需>0.5)"

def _track_convergence_streak(goal_id: str, converged: bool, db: Session) -> int:
    """
    跟踪连续收敛次数。

    每次收敛判断后调用：收敛→计数+1，不收敛→重置为0。
    连续3次收敛时触发自动执行。
    返回当前连续收敛计数。
    """
    # 从 goals 表的 extra_data 或专用表读取当前计数
    # 简单方式：写到一个专用 key-value 记录（用 JSON 存于 goals.extra_data）
    row = db.execute(
        text("SELECT extra_data FROM goals WHERE id = :gid"),
        {"gid": goal_id}
    ).fetchone()

    extra: Dict[str, Any] = {}
    if row and row[0]:
        try:
            extra = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            extra = {}

    streak = extra.get("convergence_streak", 0)

    if converged:
        streak += 1
        extra["convergence_streak"] = streak
        extra["last_convergence_check"] = datetime.utcnow().isoformat()
        if streak >= 3:
            extra["convergence_streak"] = 0  # 重置
            extra["auto_execute_triggered"] = datetime.utcnow().isoformat()
            logger.info(f"[check_convergence] goal={goal_id} streak={streak} → 自动执行已触发！")
        else:
            logger.info(f"[check_convergence] goal={goal_id} streak={streak}")
    else:
        streak = 0
        extra["convergence_streak"] = 0
        extra["last_convergence_check"] = datetime.utcnow().isoformat()
        logger.info(f"[check_convergence] goal={goal_id} streak=0 (not converged)")

    extra_json = _serialize(extra)
    db.execute(
        text("UPDATE goals SET extra_data = :extra WHERE id = :gid"),
        {"gid": goal_id, "extra": extra_json}
    )
    db.commit()

    return streak

# ============ 探索模式闭环核心函数 ============

