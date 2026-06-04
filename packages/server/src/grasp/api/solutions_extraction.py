from sqlalchemy import text
import json
from fastapi import HTTPException
# -*- coding: utf-8 -*-
from loguru import logger

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from reins.common.database import get_db

from fastapi import APIRouter
router = APIRouter()

def _extract_constraints_from_discussion(discussion: List[Dict[str, Any]], goal_id: str, db: Session) -> Dict[str, Any]:
    """
    从讨论历史中提取约束调整意图（MVP: 关键词匹配）。

    提取规则：
    - "工期 X 天" / "工期保持X天" → duration_days: X
    - "工期缩短" → 上一轮工期 × 0.9
    - "工期延长" → 上一轮工期 × 1.1
    - "工期不变" → 保持上一轮工期
    - "成本 X" / "成本降低X%" → cost: 调整
    - "成本收紧" → 上一轮成本 × 0.9
    - "安全系数 X" / "安全提高" → safety: 调整
    - "安全降低" → safety × 0.9

    返回：
    {
        "extracted": {"duration_days": 2, "cost_pct": -5, ...},
        "full_constraints": {"duration_days": 2, "cost_usd": 950, ...}
    }
    """
    import re

    # 收集所有 human 消息
    human_messages = [msg.get("content", "") for msg in discussion if msg.get("role") == "human"]
    combined_text = " ".join(human_messages)
    text_lower = combined_text.lower()

    extracted: Dict[str, Any] = {}

    # ---------- 工期提取 ----------
    # "工期保持2天" / "工期保持 2 天" / "工期 2 天"
    duration_match = re.search(r'工期\s*(?:保持|设为|设置|为|是)?\s*(\d+(?:\.\d+)?)\s*天', combined_text)
    if duration_match:
        extracted["duration_days"] = float(duration_match.group(1))
    elif "工期不变" in combined_text or "工期保持" in combined_text:
        extracted["duration_days"] = "keep"
    elif "工期缩短" in combined_text or "工期收紧" in combined_text:
        extracted["duration_days"] = "tighten"
    elif "工期延长" in combined_text or "工期放宽" in combined_text:
        extracted["duration_days"] = "loosen"
    elif re.search(r'工期.*\d+', combined_text):
        # 尝试提取数字
        num_match = re.search(r'工期.*?(\d+(?:\.\d+)?)', combined_text)
        if num_match:
            extracted["duration_days"] = float(num_match.group(1))

    # ---------- 成本提取 ----------
    # "成本收紧5%" / "成本降低5%" / "成本5%"
    cost_pct_match = re.search(r'成本\s*(?:收紧|降低|减少|下降|降)\s*(\d+(?:\.\d+)?)\s*%', combined_text)
    if cost_pct_match:
        extracted["cost_pct"] = -float(cost_pct_match.group(1))
    else:
        cost_pct_match2 = re.search(r'成本\s*(?:增加|提高|上涨|涨|放宽)\s*(\d+(?:\.\d+)?)\s*%', combined_text)
        if cost_pct_match2:
            extracted["cost_pct"] = float(cost_pct_match2.group(1))
        elif re.search(r'成本\s*(?:设为|设置|为|是)?\s*(\d+(?:\.\d+)?)', combined_text):
            cost_num_match = re.search(r'成本\s*(?:设为|设置|为|是)?\s*(\d+(?:\.\d+)?)', combined_text)
            if cost_num_match:
                extracted["cost_usd"] = float(cost_num_match.group(1))
        elif "成本降低" in combined_text or "成本收紧" in combined_text:
            extracted["cost_pct"] = -10  # 默认收紧10%
        elif "成本增加" in combined_text or "成本放宽" in combined_text:
            extracted["cost_pct"] = 10  # 默认放宽10%
        elif "成本不变" in combined_text:
            extracted["cost_pct"] = 0

    # ---------- 安全系数提取 ----------
    safety_num_match = re.search(r'(?:安全系数|安全)\s*(?:设为|设置|为|是|到|提高到|降低到)?\s*(\d+(?:\.\d+)?)', combined_text)
    if safety_num_match:
        extracted["safety_score"] = float(safety_num_match.group(1))
    elif "安全提高" in combined_text or "安全收紧" in combined_text:
        extracted["safety_action"] = "tighten"
    elif "安全降低" in combined_text or "安全放宽" in combined_text:
        extracted["safety_action"] = "loosen"
    elif "安全不变" in combined_text:
        extracted["safety_action"] = "keep"

    # ---------- 通用意图提取 ----------
    # 如果用户说了 "调整X"、"放宽X"、"收紧X"
    for target in ["工期", "成本", "安全"]:
        if f"{target}调整" in combined_text and f"{target}" not in str(extracted):
            extracted[f"{target}_action"] = "adjust"
        if f"{target}放宽" in combined_text and f"{target}" not in str(extracted):
            extracted[f"{target}_action"] = "loosen"
        if f"{target}收紧" in combined_text and f"{target}" not in str(extracted):
            extracted[f"{target}_action"] = "tighten"

    # ---------- 构建完整约束 ----------
    # 获取上一轮约束作为基准
    prev_cons_row = db.execute(
        text("""
            SELECT constraints FROM iteration_constraints
            WHERE goal_id = :gid ORDER BY round DESC LIMIT 1
        """),
        {"gid": goal_id}
    ).mappings().fetchone()

    base_constraints: Dict[str, Any] = {}
    if prev_cons_row and prev_cons_row.get("constraints"):
        raw = prev_cons_row["constraints"]
        if isinstance(raw, str):
            try:
                base_constraints = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                base_constraints = {}
        elif isinstance(raw, dict):
            base_constraints = raw

    # 同时从最优方案获取参数作为补充基准
    best_sol_row = db.execute(
        text("""
            SELECT parameters FROM solutions
            WHERE goal_id = :gid AND is_optimal = 1
            ORDER BY round DESC LIMIT 1
        """),
        {"gid": goal_id}
    ).mappings().fetchone()

    if best_sol_row and best_sol_row.get("parameters") and not base_constraints:
        raw = best_sol_row["parameters"]
        if isinstance(raw, str):
            try:
                base_constraints = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
        elif isinstance(raw, dict):
            base_constraints = raw

    full_constraints: Dict[str, Any] = dict(base_constraints)

    # 应用提取的约束调整
    reason_parts = []

    # 工期
    dur_val = extracted.get("duration_days")
    if dur_val is not None:
        if isinstance(dur_val, (int, float)):
            full_constraints["duration_days"] = dur_val
            reason_parts.append(f"工期 → {dur_val}天（用户指定）")
        elif dur_val == "keep":
            # 保持原值，不变
            reason_parts.append("工期保持不变")
        elif dur_val == "tighten":
            old = base_constraints.get("duration_days")
            if old:
                num = _parse_number_safe(old)
                if num:
                    full_constraints["duration_days"] = round(num * 0.9, 2)
                    reason_parts.append(f"工期缩短 10%（{old} → {full_constraints['duration_days']}天）")
                else:
                    full_constraints["duration_days"] = "tightened"
                    reason_parts.append("工期缩短（无法解析原值）")
            else:
                full_constraints["duration_days"] = "tightened"
                reason_parts.append("工期缩短（无基准值）")
        elif dur_val == "loosen":
            old = base_constraints.get("duration_days")
            if old:
                num = _parse_number_safe(old)
                if num:
                    full_constraints["duration_days"] = round(num * 1.1, 2)
                    reason_parts.append(f"工期延长 10%（{old} → {full_constraints['duration_days']}天）")

    # 成本
    cost_pct = extracted.get("cost_pct")
    cost_usd = extracted.get("cost_usd")
    if cost_usd is not None:
        full_constraints["cost_usd"] = cost_usd
        reason_parts.append(f"成本 → ${cost_usd}（用户指定）")
    elif cost_pct is not None:
        old = base_constraints.get("cost_usd") or base_constraints.get("成本") or base_constraints.get("cost")
        if old is not None:
            num = _parse_number_safe(old)
            if num:
                new_cost = round(num * (1 + cost_pct / 100), 2)
                full_constraints["cost_usd"] = new_cost
                reason_parts.append(f"成本调整 {cost_pct:+}%（{old} → ${new_cost}）")
            else:
                full_constraints["cost_usd"] = f"adjusted_{cost_pct:+}%"
                reason_parts.append(f"成本调整 {cost_pct:+}%（无法解析原值）")
        else:
            full_constraints["cost_pct_adjustment"] = cost_pct
            reason_parts.append(f"成本调整 {cost_pct:+}%（无基准值）")

    # 安全系数
    safety_num = extracted.get("safety_score")
    safety_action = extracted.get("safety_action")
    if safety_num is not None:
        full_constraints["safety_score"] = safety_num
        reason_parts.append(f"安全系数 → {safety_num}（用户指定）")
    elif safety_action:
        old = base_constraints.get("safety_score") or base_constraints.get("安全系数")
        if safety_action == "tighten":
            if old is not None:
                num = _parse_number_safe(old)
                if num:
                    full_constraints["safety_score"] = round(num * 1.05, 2)
                    reason_parts.append(f"安全提高 5%（{old} → {full_constraints['safety_score']}）")
            else:
                full_constraints["safety_score"] = "tightened"
                reason_parts.append("安全提高（无基准值）")
        elif safety_action == "loosen":
            if old is not None:
                num = _parse_number_safe(old)
                if num:
                    full_constraints["safety_score"] = round(num * 0.95, 2)
                    reason_parts.append(f"安全降低 5%（{old} → {full_constraints['safety_score']}）")
            else:
                full_constraints["safety_score"] = "loosened"
                reason_parts.append("安全降低（无基准值）")

    return {
        "extracted": extracted,
        "full_constraints": full_constraints,
        "reason": "共识达成，约束调整：" + "；".join(reason_parts) if reason_parts else "共识达成",
        "has_adjustments": bool(extracted),
    }

def _parse_number_safe(val: Any) -> float | None:
    """安全地从任意值中提取数字"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        import re
        m = re.search(r'[-+]?\d*\.?\d+', val)
        if m:
            return float(m.group())
    return None

