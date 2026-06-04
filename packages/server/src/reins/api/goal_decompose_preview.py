"""
目标分解预览端点
从 goal_decompose.py 拆分出的 preview 模块
"""
import json
from loguru import logger
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

from shared.database import get_db_session
from models.goal import Goal
from services.llm_service import llm_service
from .goal_decompose_helpers import (
    _get_scenario_guide,
    _build_decomposition_prompt_with_scenario,
    DECOMPOSITION_SYSTEM_PROMPT,
)

router = APIRouter()

def _call_llm_and_validate(goal_title: str, goal_description: Optional[str],
                           scenario_guide: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """调用 LLM 进行分解并验证结果"""
    user_prompt = _build_decomposition_prompt_with_scenario(
        goal_title, goal_description, scenario_guide
    )

    messages = [
        {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    response = llm_service.chat_completion(
        messages,
        response_format={"type": "json_object"},
    )

    if response.startswith("```"):
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end != 0:
            response = response[start:end]

    result = json.loads(response)
    projects = result.get("projects", [])

    validated_projects = []
    for i, proj in enumerate(projects):
        validated_proj = {
            "name": proj.get("name", f"项目 {i+1}"),
            "description": proj.get("description", ""),
            "priority": proj.get("priority", "medium"),
            "category": proj.get("category", "other"),
            "depends_on": proj.get("depends_on", []),
        }
        if validated_proj["priority"] not in ("low", "medium", "high"):
            validated_proj["priority"] = "medium"
        if validated_proj["category"] not in ("research", "design", "implementation", "testing", "review", "other"):
            validated_proj["category"] = "other"
        validated_proj["depends_on"] = [
            idx for idx in validated_proj["depends_on"]
            if isinstance(idx, int) and 0 <= idx < i
        ]
        validated_projects.append(validated_proj)

    return validated_projects

@router.post("/{goal_id}/auto-decompose")
def preview_auto_decompose_goal(
    goal_id: str,
    use_scenario: bool = Query(True, description="是否使用 Grasp 认知注入"),
):
    """自动分解目标为子项目（预览模式，不持久化）"""
    db = get_db_session()

    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        scenario_guide = None
        if use_scenario:
            scenario_guide = _get_scenario_guide(goal_id, goal.title, goal.description, db)
            if scenario_guide:
                logger.info(f"[goal_decompose] 使用场景指南: {scenario_guide.get('name', 'unnamed')}")

        try:
            validated_projects = _call_llm_and_validate(
                goal.title, goal.description, scenario_guide
            )

            if not validated_projects:
                logger.info(f"[goal_decompose] LLM 返回空，目标: {goal.title}")
                return {"success": False, "error": "LLM 返回空项目列表"}

            logger.info(f"[goal_decompose] 目标分解成功（预览）: {goal.title} → {len(validated_projects)} 个子项目")

        except json.JSONDecodeError as e:
            logger.info(f"[goal_decompose] JSON 解析失败: {e}")
            raise HTTPException(status_code=500, detail=f"LLM 返回格式无效: {e}")
        except Exception as e:
            logger.info(f"[goal_decompose] 目标分解失败: {e}")
            raise HTTPException(status_code=500, detail=f"目标分解失败: {str(e)}")

        return {
            "success": True,
            "goal_id": goal_id,
            "goal_title": goal.title,
            "project_count": len(validated_projects),
            "projects": validated_projects,
        }

    finally:
        if db:
            db.close()

@router.post("/{goal_id}/auto-decompose/preview")
def preview_auto_decompose(
    goal_id: str,
    use_scenario: bool = Query(True, description="是否使用 Grasp 认知注入"),
):
    """预览自动分解结果（只分解不创建项目）"""
    db = get_db_session()

    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        scenario_guide = None
        if use_scenario:
            scenario_guide = _get_scenario_guide(goal_id, goal.title, goal.description, db)

        try:
            validated_projects = _call_llm_and_validate(
                goal.title, goal.description, scenario_guide
            )

            if not validated_projects:
                return {"success": False, "error": "LLM 返回空项目列表", "projects": []}

            return {
                "success": True,
                "goal_id": goal_id,
                "goal_title": goal.title,
                "project_count": len(validated_projects),
                "scenario_used": use_scenario and scenario_guide is not None,
                "scenario": {
                    "id": scenario_guide["id"],
                    "name": scenario_guide["name"],
                } if scenario_guide else None,
                "projects": validated_projects,
            }

        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"LLM 返回格式无效: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"目标分解失败: {str(e)}")

    finally:
        if db:
            db.close()
