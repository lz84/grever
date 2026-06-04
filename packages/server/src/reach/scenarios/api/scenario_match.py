"""
Scenario matching endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
import difflib

from reins.common.database import get_db_manager
from sqlalchemy import text
from .scenario_models import (
    ScenarioMatchResponse, MatchPreviewRequest, MatchPreviewResponse,
    ScenarioMatchItem, MATCH_THRESHOLD, _parse_json,
)

router = APIRouter(tags=["scenario-match"])

def _calc_score(title: str, desc: str, sc: dict) -> float:
    text_content = f"{title} {desc or ''}".lower()
    cat_kws = {
        "earthquake": ["地震", "震级", "震源", "救援", "搜救", "震后"],
        "flood": ["洪水", "洪涝", "水位", "暴雨", "防汛", "泄洪", "淹"],
        "chemical": ["危化品", "泄漏", "化工", "有毒气体", "化学品", "泄漏事故"],
    }
    cat = sc.get("category", "").lower()
    if cat in cat_kws:
        kws = cat_kws[cat]
        m = sum(1 for kw in kws if kw in text_content)
        if m:
            return min(0.7 + m / len(kws) * 0.3, 1.0)
    name = sc.get("name", "").lower()
    ratio = difflib.SequenceMatcher(None, title.lower(), name).ratio()
    return min(ratio * 0.6, 1.0)

def _build_match_item(sc: dict, score: float) -> ScenarioMatchItem:
    dag = _parse_json(sc.get("template_dag"))
    phase_count = len(dag.get("nodes", [])) if dag else 0
    return ScenarioMatchItem(
        scenario_id=sc["id"], name=sc["name"], category=sc["category"],
        level=sc.get("level") or "goal", match_score=round(score, 3),
        trust_level=sc.get("trust_level") or "low", usage_count=sc.get("usage_count") or 0,
        description=sc.get("description") or "", phase_count=phase_count,
    )

@router.post("/api/v1/scenarios/match-for-goal/{goal_id}", response_model=ScenarioMatchResponse)
def match_scenario(goal_id: str, limit: int = Query(3, ge=1, le=10)):
    """为 Goal 匹配 Scenario"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        goal = conn.execute(text(
            "SELECT id, title, description FROM goals WHERE id = :id"
        ), {"id": goal_id}).fetchone()
    if not goal:
        raise HTTPException(404, f"Goal not found: {goal_id}")

    goal_title = goal[1] or ""
    goal_desc = goal[2] or ""

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, name, category, level, template_dag, description,
                   scenario_desc, trust_level, source, usage_count
            FROM scenarios WHERE status = 'active'
        """)).fetchall()

    matches = []
    for row in rows:
        sc = {
            "id": row[0], "name": row[1], "category": row[2],
            "level": row[3], "template_dag": row[4],
            "description": row[5], "scenario_desc": row[6],
            "trust_level": row[7], "source": row[8], "usage_count": row[9],
        }
        if not sc["template_dag"]:
            continue
        score = _calc_score(goal_title, goal_desc, sc)
        matches.append(_build_match_item(sc, score))

    matches.sort(key=lambda m: m.match_score, reverse=True)
    top_score = matches[0].match_score if matches else 0.0
    return ScenarioMatchResponse(
        goal_id=goal_id,
        goal_title=goal_title,
        matches=matches[:limit],
        threshold_met=top_score >= MATCH_THRESHOLD,
        threshold=MATCH_THRESHOLD,
    )

@router.post("/api/v1/scenarios/match-preview", response_model=MatchPreviewResponse)
def match_scenario_preview(req: MatchPreviewRequest, limit: int = Query(3, ge=1, le=10)):
    """预览场景匹配（不需要 goal_id，适用于创建前预览）"""
    goal_title = req.title or ""
    goal_desc = req.description or ""

    engine = get_db_manager().engine
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, name, category, level, template_dag, description,
                   scenario_desc, trust_level, source, usage_count
            FROM scenarios WHERE status = 'active'
        """)).fetchall()

    matches = []
    for row in rows:
        sc = {
            "id": row[0], "name": row[1], "category": row[2],
            "level": row[3], "template_dag": row[4],
            "description": row[5], "scenario_desc": row[6],
            "trust_level": row[7], "source": row[8], "usage_count": row[9],
        }
        if not sc["template_dag"]:
            continue
        score = _calc_score(goal_title, goal_desc, sc)
        matches.append(_build_match_item(sc, score))

    matches.sort(key=lambda m: m.match_score, reverse=True)
    top_score = matches[0].match_score if matches else 0.0
    return MatchPreviewResponse(
        title=goal_title,
        matches=matches[:limit],
        threshold_met=top_score >= MATCH_THRESHOLD,
        threshold=MATCH_THRESHOLD,
    )


# === Create (merged from scenario_create.py) ===
"""
Scenario creation endpoints (LLM-based).
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import json
import uuid
import re

from reins.common.database import get_db_manager
from services.llm_service import llm_service
from sqlalchemy import text
from .scenario_models import CreateScenarioResponse, _parse_json

router = APIRouter(tags=["scenario-create"])

@router.post("/api/v1/scenarios/create-for-goal/{goal_id}", response_model=CreateScenarioResponse)
def create_scenario_for_goal(goal_id: str):
    """为目标创建新场景（LLM 生成）"""
    db_manager = get_db_manager()

    with db_manager.engine.connect() as conn:
        goal = conn.execute(text(
            "SELECT id, title, description FROM goals WHERE id = :id"
        ), {"id": goal_id}).fetchone()

    if not goal:
        raise HTTPException(404, f"Goal not found: {goal_id}")

    goal_title = goal[1] or ""
    goal_desc = goal[2] or ""

    prompt = f"""为一个目标创建工作场景。该目标是：{goal_title}
目标描述：{goal_desc or '无'}

请生成一个适用的工作场景 JSON，格式如下：
{{
  "name": "场景名称",
  "category": "general|earthquake|flood|chemical|fire|software|business|other 之一",
  "description": "一句话描述",
  "scenario_desc": "详细场景描述，包含目标、步骤、注意事项",
  "steps": [
    {{"order": 1, "name": "步骤1名称", "description": "步骤1描述", "agent_type": "executor|analyst|reviewer|coordinator 之一"}},
    {{"order": 2, "name": "步骤2名称", "description": "步骤2描述", "agent_type": "executor"}}
  ]
}}

要求：
- steps 至少 2 步，最多 5 步
- 每步需要有 order、name、description、agent_type
- category 根据目标类型选择，通用目标用 general

请只返回 JSON，不要其他文字。"""

    messages = [{"role": "user", "content": prompt}]
    raw = llm_service.chat_completion(messages, response_format={"type": "json_object"})

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        try:
            if isinstance(raw, str):
                json_match = re.search(r'\{[\s\S]*\}', raw)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise HTTPException(500, f"LLM 返回格式异常，无法解析: {raw[:200]}")
            else:
                raise HTTPException(500, f"LLM 返回非字符串: {type(raw)}")
        except json.JSONDecodeError as e:
            raise HTTPException(500, f"JSON 解析失败: {e}, 原始内容: {raw[:200]}")

    name = data.get("name", f"{goal_title} 场景")
    category = data.get("category", "general")
    description = data.get("description", "")
    scenario_desc = data.get("scenario_desc", "")
    steps = data.get("steps", [])

    nodes = []
    for s in steps:
        nodes.append({
            "id": f"step_{s['order']}",
            "type": "step",
            "name": s["name"],
            "description": s.get("description", ""),
            "agent_type": s.get("agent_type", "executor"),
        })

    edges = []
    for i in range(len(nodes) - 1):
        edges.append({
            "source": nodes[i]["id"],
            "target": nodes[i + 1]["id"],
        })

    template_dag = {"nodes": nodes, "edges": edges}

    scenario_id = f"scenario-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    with db_manager.engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO scenarios
            (id, name, category, level, status, version,
             description, scenario_desc, template_dag, trust_level,
             source, usage_count, success_rate, avg_duration_ms,
             created_at, updated_at)
            VALUES
            (:id, :name, :category, 'project', 'active', 1,
             :desc, :scenario_desc, :dag, 'medium',
             'llm_generated', 0, NULL, NULL,
             :now, :now)
        """), {
            "id": scenario_id,
            "name": name,
            "category": category,
            "desc": description,
            "scenario_desc": scenario_desc,
            "dag": json.dumps(template_dag, ensure_ascii=False),
            "now": now,
        })
        conn.commit()

    return CreateScenarioResponse(
        scenario_id=scenario_id,
        name=name,
        category=category,
        description=description,
        phase_count=len(nodes),
    )

