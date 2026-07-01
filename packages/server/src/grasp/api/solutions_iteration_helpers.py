from sqlalchemy.orm import Session
from sqlalchemy import func
import json
from fastapi import HTTPException
from models.solution import Solution
from models.iteration_constraint import IterationConstraint
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from reins.common.database import get_db
from pydantic import BaseModel, Field
from fastapi import APIRouter

router = APIRouter()

class CreateIterationRequest(BaseModel):
    """创建迭代请求（空 body 即可，自动生成 iteration_number）"""
    pass

class DiscussRequest(BaseModel):
    """讨论消息请求"""
    role: str = Field(..., description="human | ai")
    content: str = Field(..., description="消息内容")

# ============ 辅助函数 ============

def _parse_discussion_list(val) -> List[Dict[str, Any]]:
    """解析 ai_discussion 字段为列表"""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            return []
    return []

def _generate_ai_analysis(goal_id: str, iter_id: str, db: Session) -> Dict[str, str]:
    """
    MVP: 基于规则生成 AI 分析（不调用外部 LLM）

    分析逻辑：
    1. 对比该 goal 下所有 solutions 的评分
    2. 检查约束变化
    3. 给出建议
    """
    # 获取该 goal 下所有方案评分
    sol_rows = db.query(Solution).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.round.asc()).all()
    sol_rows = [
        {"id": s.id, "round": s.round, "name": s.name, "score": s.score, "status": s.status, "is_optimal": s.is_optimal}
        for s in sol_rows
    ]

    if not sol_rows:
        return {
            "analysis": "当前暂无方案数据，建议先执行探索任务生成初始方案。",
            "suggestion": "启动第一轮探索，收集初始方案后进行评分比较。"
        }

    scores = [r.get("score") for r in sol_rows if r.get("score") is not None]
    total_solutions = len(sol_rows)
    optimal = next((r for r in sol_rows if r.get("is_optimal")), None)

    # 分析评分趋势
    if len(scores) >= 2:
        first_score = scores[0]
        last_score = scores[-1]
        improvement = last_score - first_score
        trend = "上升" if improvement > 0 else "下降" if improvement < 0 else "持平"
        score_analysis = (
            f"共 {total_solutions} 个方案，评分范围 [{min(scores):.2f}, {max(scores):.2f}]，"
            f"趋势{trend}（{first_score:.2f} → {last_score:.2f}，变化 {improvement:+.2f}）"
        )
    else:
        score_analysis = f"仅有 {total_solutions} 个方案（评分 {scores[0]:.2f if scores else 'N/A'}），" \
                         f"需要更多轮次迭代来观察趋势。"

    # 最优方案信息
    optimal_info = ""
    if optimal:
        optimal_info = f"当前最优方案为 Round {optimal['round']}「{optimal['name']}」（score={optimal['score']:.2f}）。"
    else:
        optimal_info = "尚未标记最优方案，建议运行多维度评分比较。"

    # 检查约束变化
    cons_rows = db.query(IterationConstraint).filter(
        IterationConstraint.goal_id == goal_id
    ).order_by(IterationConstraint.round.desc()).limit(2).all()
    cons_rows = [{"round": c.round, "constraints": c.constraints} for c in cons_rows]

    constraint_info = ""
    if len(cons_rows) >= 2:
        latest_cons = _parse_json_field(cons_rows[0].get("constraints")) or {}
        prev_cons = _parse_json_field(cons_rows[1].get("constraints")) or {}
        changed_keys = set(latest_cons.keys()) - set(prev_cons.keys())
        if changed_keys:
            constraint_info = f"最近一轮约束有 {len(changed_keys)} 项变更：{', '.join(list(changed_keys)[:5])}。"
        else:
            constraint_info = "约束条件保持稳定，无重大调整。"
    elif cons_rows:
        constraint_info = "约束历史较短，建议积累更多轮次后分析。"
    else:
        constraint_info = "尚未建立约束记录，建议设置初始约束参数。"

    # 综合分析与建议
    analysis_parts = [score_analysis, optimal_info, constraint_info]
    analysis = " | ".join(p for p in analysis_parts if p)

    # 建议生成
    if len(scores) >= 2 and len(scores) <= 1:
        suggestion = "当前方案较少，建议继续探索新方案。"
    elif scores and max(scores) < 60:
        suggestion = "方案评分普遍偏低，建议调整约束条件或探索不同方向的方案。"
    elif scores and max(scores) < 80:
        suggestion = "已有方案评分中等，建议通过微调参数进一步优化当前最优方案。"
    elif scores and max(scores) >= 80:
        suggestion = "已有高分方案，可以考虑收敛或针对薄弱环节做最后一轮优化。"
    else:
        suggestion = "继续迭代，积累更多方案以进行充分比较。"

    return {"analysis": analysis, "suggestion": suggestion}

# ================================================================
# Sprint 78: 共识检测与约束自动提取
# ================================================================

# 共识关键词（人的消息包含这些词时，认为讨论达成共识）
CONSENSUS_KEYWORDS = ["可以", "执行", "同意", "开始", "就这样", "确定了", "确认", "ok", "好的", "通过", "批准", "认可", "没问题"]

def _detect_consensus(discussion: List[Dict[str, Any]]) -> bool:
    """
    检测讨论是否达成共识。

    逻辑：检查最后一条 human 消息是否包含共识关键词。
    """
    # 从后往前找最后一条 human 消息
    for msg in reversed(discussion):
        if msg.get("role") == "human":
            content = msg.get("content", "").lower()
            return any(kw in content for kw in CONSENSUS_KEYWORDS)
    return False

