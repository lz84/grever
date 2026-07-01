"""
优化循环引擎 — 方案比较 + 收敛判断 + 约束调整

OptimizationLoop 类，状态机：
idle → comparing → converging → converged
"""

import json
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text

class OptimizationLoopState:
    IDLE = 'idle'
    COMPARING = 'comparing'
    CONVERGING = 'converging'
    CONVERGED = 'converged'

class OptimizationLoop:
    """
    迭代优化循环引擎

    状态机: idle → comparing → converging → converged
    """

    def __init__(self, db_session_factory):
        """
        Args:
            db_session_factory: SQLAlchemy session factory
        """
        self._session_factory = db_session_factory
        self._state = OptimizationLoopState.IDLE
        self._goal_id: Optional[str] = None

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str):
        valid_states = {
            OptimizationLoopState.IDLE,
            OptimizationLoopState.COMPARING,
            OptimizationLoopState.CONVERGING,
            OptimizationLoopState.CONVERGED,
        }
        if value not in valid_states:
            raise ValueError(f"Invalid state: {value}. Must be one of {valid_states}")
        logger.info(f"[OptimizationLoop] State transition: {self._state} → {value} (goal: {self._goal_id})")
        self._state = value

    def _get_db(self):
        """获取数据库会话"""
        return self._session_factory()

    def start(self, goal_id: str):
        """启动优化循环"""
        self._goal_id = goal_id
        self.state = OptimizationLoopState.COMPARING
        logger.info(f"[OptimizationLoop] Started for goal {goal_id}")

    def stop(self):
        """停止优化循环"""
        self._goal_id = None
        self.state = OptimizationLoopState.IDLE

    # ======== 方案比较 ========

    def compare_solutions(self, goal_id: str) -> Dict[str, Any]:
        """
        比较当前方案 vs 历史方案

        Returns:
            {
                "goal_id": str,
                "total": int,
                "current_round": int,
                "solutions": [...],
                "best": {...},
                "improvement": float,  # 相比上一轮的改进百分比
                "state": str,
            }
        """
        db = self._get_db()
        try:
            self.state = OptimizationLoopState.COMPARING

            rows = db.execute(
                text("""
                    SELECT * FROM solutions WHERE goal_id = :gid
                    ORDER BY round ASC, score DESC
                """),
                {"gid": goal_id}
            ).mappings().fetchall()

            solutions = []
            for r in rows:
                solutions.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "round": r.get("round"),
                    "score": r.get("score"),
                    "status": r.get("status"),
                    "is_optimal": bool(r.get("is_optimal", 0)),
                    "parameters": self._parse_json(r.get("parameters")),
                    "dimensions": self._parse_json(r.get("dimensions")),
                })

            # 找最优方案
            best = None
            best_score = None
            for s in solutions:
                if s.get("is_optimal"):
                    best = s
                    break
                if s.get("score") is not None:
                    if best_score is None or s["score"] > best_score:
                        best_score = s["score"]
                        best = s

            # 计算改进幅度
            improvement = self._calculate_improvement(solutions)

            # 获取当前轮次
            current_round = max((s.get("round", 1) for s in solutions), default=1)

            result = {
                "goal_id": goal_id,
                "total": len(solutions),
                "current_round": current_round,
                "solutions": solutions,
                "best": best,
                "improvement": improvement,
                "state": self._state,
            }

            # 根据改进幅度决定下一步
            if improvement < 0.05:  # 改进 < 5%
                self.state = OptimizationLoopState.CONVERGING
                result["state"] = self._state
                result["recommendation"] = "converging — improvement below threshold"
            else:
                result["recommendation"] = "continue iterating"

            return result

        finally:
            db.close()

    def _calculate_improvement(self, solutions: List[Dict]) -> float:
        """计算最近两轮之间的改进百分比"""
        if len(solutions) < 2:
            return 1.0  # 只有一轮时认为有充分改进空间

        # 按 round 分组，取每轮最高分
        round_scores: Dict[int, float] = {}
        for s in solutions:
            rnd = s.get("round", 1)
            score = s.get("score")
            if score is not None:
                if rnd not in round_scores or score > round_scores[rnd]:
                    round_scores[rnd] = score

        if len(round_scores) < 2:
            return 1.0

        rounds_sorted = sorted(round_scores.keys())
        prev_score = round_scores[rounds_sorted[-2]]
        curr_score = round_scores[rounds_sorted[-1]]

        if prev_score == 0:
            return 1.0

        return (curr_score - prev_score) / prev_score

    # ======== 收敛判断 ========

    def check_convergence(self, goal_id: str) -> Dict[str, Any]:
        """
        收敛判断逻辑

        改进 < 5% 触发人类确认
        改进 < 1% 自动收敛

        Returns:
            {
                "converged": bool,
                "requires_human_confirmation": bool,
                "improvement": float,
                "current_round": int,
                "message": str,
            }
        """
        db = self._get_db()
        try:
            self.state = OptimizationLoopState.CONVERGING

            # 获取收敛阈值
            from models.goal import Goal
            goal = db.query(Goal).filter(Goal.id == goal_id).first()
            threshold = goal.convergence_threshold if goal and goal.convergence_threshold is not None else 0.05
            max_rounds = goal.max_rounds if goal and goal.max_rounds is not None else 10

            # 获取方案
            rows = db.execute(
                text("""
                    SELECT round, score FROM solutions WHERE goal_id = :gid
                    ORDER BY round ASC, score DESC
                """),
                {"gid": goal_id}
            ).mappings().fetchall()

            if len(rows) < 2:
                return {
                    "converged": False,
                    "requires_human_confirmation": False,
                    "improvement": 1.0,
                    "current_round": 1,
                    "message": "需要至少 2 轮方案才能判断收敛",
                }

            # 按 round 取最高分
            round_scores: Dict[int, float] = {}
            for r in rows:
                rnd = r.get("round", 1)
                score = r.get("score")
                if score is not None:
                    if rnd not in round_scores or score > round_scores[rnd]:
                        round_scores[rnd] = score

            rounds_sorted = sorted(round_scores.keys())
            current_round = rounds_sorted[-1]

            # 检查是否达到最大轮次
            if current_round >= max_rounds:
                self.state = OptimizationLoopState.CONVERGED
                return {
                    "converged": True,
                    "requires_human_confirmation": False,
                    "improvement": 0.0,
                    "current_round": current_round,
                    "message": f"已达到最大轮次 {max_rounds}，自动收敛",
                }

            # 计算改进
            if len(rounds_sorted) < 2:
                return {
                    "converged": False,
                    "requires_human_confirmation": False,
                    "improvement": 1.0,
                    "current_round": current_round,
                    "message": "只有一轮有分数，继续迭代",
                }

            prev_score = round_scores[rounds_sorted[-2]]
            curr_score = round_scores[rounds_sorted[-1]]

            if prev_score == 0:
                improvement = 1.0
            else:
                improvement = abs(curr_score - prev_score) / prev_score

            # 判断收敛
            if improvement < 0.01:  # < 1% 自动收敛
                self.state = OptimizationLoopState.CONVERGED
                return {
                    "converged": True,
                    "requires_human_confirmation": False,
                    "improvement": improvement,
                    "current_round": current_round,
                    "message": f"改进 {improvement:.1%} < 1%，自动收敛",
                }
            elif improvement < threshold:  # < 5% 触发人类确认
                return {
                    "converged": False,
                    "requires_human_confirmation": True,
                    "improvement": improvement,
                    "current_round": current_round,
                    "message": f"改进 {improvement:.1%} < {threshold:.0%}，需要人类确认是否继续",
                }
            else:
                return {
                    "converged": False,
                    "requires_human_confirmation": False,
                    "improvement": improvement,
                    "current_round": current_round,
                    "message": f"改进 {improvement:.1%} >= {threshold:.0%}，继续迭代",
                }

        finally:
            db.close()

    # ======== 约束调整 ========

    def adjust_constraints(self, goal_id: str) -> Dict[str, Any]:
        """
        自动调整约束

        - 最短工期 × 0.9
        - 最低成本 × 0.9
        - 综合各收紧 5%

        Returns:
            {
                "goal_id": str,
                "round": int,
                "previous_constraints": {...},
                "adjusted_constraints": {...},
            }
        """
        db = self._get_db()
        try:
            # 获取上一轮约束
            prev_row = db.execute(
                text("""
                    SELECT constraints, round FROM iteration_constraints
                    WHERE goal_id = :gid
                    ORDER BY round DESC, created_at DESC LIMIT 1
                """),
                {"gid": goal_id}
            ).mappings().fetchone()

            prev_constraints = {}
            prev_round = 0
            if prev_row:
                prev_round = prev_row.get("round", 0)
                c_raw = prev_row.get("constraints")
                if c_raw:
                    if isinstance(c_raw, str):
                        try:
                            prev_constraints = json.loads(c_raw)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif isinstance(c_raw, dict):
                        prev_constraints = c_raw

            next_round = prev_round + 1

            # 调整约束
            adjusted = {}

            # 最短工期 × 0.9
            for key in ("最短工期", "duration"):
                if key in prev_constraints:
                    val = prev_constraints[key]
                    if isinstance(val, (int, float)):
                        adjusted[key] = round(val * 0.9, 2)

            # 最低成本 × 0.9
            for key in ("最低成本", "cost"):
                if key in prev_constraints:
                    val = prev_constraints[key]
                    if isinstance(val, (int, float)):
                        adjusted[key] = round(val * 0.9, 2)

            # 综合各收紧 5%
            for key, val in prev_constraints.items():
                if key not in adjusted and isinstance(val, (int, float)) and val > 0:
                    adjusted[key] = round(val * 0.95, 2)

            # 默认约束
            if not adjusted:
                adjusted = {
                    "最短工期": "需设置",
                    "最低成本": "需设置",
                    "安全系数": "≥1.0",
                }

            # 记录到数据库
            import uuid
            ic_id = f"ic-{uuid.uuid4().hex[:12]}"
            db.execute(
                text("""
                    INSERT INTO iteration_constraints (id, goal_id, round, constraints, reason, created_by, created_at)
                    VALUES (:id, :goal_id, :round, :constraints, :reason, :created_by, :created_at)
                """),
                {
                    "id": ic_id,
                    "goal_id": goal_id,
                    "round": next_round,
                    "constraints": json.dumps(adjusted, ensure_ascii=False),
                    "reason": "Auto-adjusted by optimization loop",
                    "created_by": "system",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            db.commit()

            return {
                "goal_id": goal_id,
                "round": next_round,
                "previous_constraints": prev_constraints,
                "adjusted_constraints": adjusted,
            }

        finally:
            db.close()

    # ======== 辅助函数 ========

    @staticmethod
    def _parse_json(value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

# ======== 便捷函数（无需实例化） ========

def compare_solutions(db, goal_id: str) -> Dict[str, Any]:
    """快捷函数：比较方案"""
    loop = OptimizationLoop(lambda: db)
    return loop.compare_solutions(goal_id)

def check_convergence(db, goal_id: str) -> Dict[str, Any]:
    """快捷函数：检查收敛"""
    loop = OptimizationLoop(lambda: db)
    return loop.check_convergence(goal_id)

def adjust_constraints(db, goal_id: str) -> Dict[str, Any]:
    """快捷函数：调整约束"""
    loop = OptimizationLoop(lambda: db)
    return loop.adjust_constraints(goal_id)
