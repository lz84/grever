# -*- coding: utf-8 -*-
"""Decomposition Fallback — E-4 默认分解提取逻辑

文档 23 号 §8.3：当 E-4 返回 insufficient 且没有附带分解产物时，
从行业包场景模板中提取默认分解。

该模块独立于 EvaluationDecompositionService，可被任何需要默认分解的地方调用。
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DecompositionFallback:
    """E-4 默认分解提取器"""

    def __init__(self, db: Session):
        self.db = db

    def extract_default_decomposition(
        self,
        goal_id: str,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        从行业包场景模板中提取默认分解。

        优先级：
        1. goals.matched_scenario_id → scenario.fullset
        2. goals.matched_scenario_id → scenario.template_dag
        3. goal.context_md → 简单解析
        4. 最终兜底：单一默认项目

        Returns:
            (projects, assumptions)
        """
        from models.goal import Goal
        from models.scenario import Scenario

        goal = self.db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            logger.warning(f"[decomposition_fallback] Goal {goal_id} not found")
            return self._create_singleton_project("Unknown Goal", ""), []

        projects = []
        assumptions: List[str] = []

        # 优先级 1&2: 从 matched_scenario 提取
        if goal.matched_scenario_id:
            scenario = self.db.query(Scenario).filter(
                Scenario.id == goal.matched_scenario_id
            ).first()
            if scenario:
                projects, assumptions = self._extract_from_scenario(scenario)

        # 优先级 3: 从 goal.context_md 解析
        if not projects and goal.context_md:
            projects = self._parse_context_md(goal.context_md)
            if projects:
                assumptions.append("从 Goal context_md 提取（无 matched_scenario）")

        # 优先级 4: 兜底
        if not projects:
            projects = self._create_singleton_project(
                goal.title or "Default Project",
                goal.description or "",
            )
            assumptions.append("使用默认分解结构（信息不充分）")

        logger.info(
            f"[decomposition_fallback] Extracted {len(projects)} projects "
            f"for goal {goal_id}, default_applied={not goal.matched_scenario_id}"
        )

        return projects, assumptions

    def _extract_from_scenario(
        self,
        scenario,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """从 scenario.fullset 或 template_dag 提取分解"""
        projects = []
        assumptions: List[str] = []

        fullset_data = self._try_parse_json(getattr(scenario, "fullset", None))
        if not fullset_data:
            fullset_data = self._try_parse_json(getattr(scenario, "template_dag", None))

        if fullset_data:
            projects = fullset_data.get("default_projects") or fullset_data.get("projects", [])
            assumptions = fullset_data.get("assumptions", [])

        # 也尝试从 scenario.steps 或 scenario.phases 提取
        if not projects:
            steps = getattr(scenario, "steps", None) or getattr(scenario, "phases", None)
            if steps:
                steps_data = self._try_parse_json(steps)
                if steps_data:
                    projects = self._convert_steps_to_projects(
                        steps_data,
                        getattr(scenario, "name", "Scenario"),
                    )

        return projects, assumptions

    def _convert_steps_to_projects(
        self,
        steps: Any,
        scenario_name: str,
    ) -> List[Dict[str, Any]]:
        """将 scenario steps/phases 转换为 project 结构"""
        if not isinstance(steps, list):
            return []

        projects_dict: Dict[str, Dict[str, Any]] = {}
        for step in steps:
            if not isinstance(step, dict):
                continue
            # 尝试多种 step 结构
            phase = step.get("phase") or step.get("stage") or step.get("name", "Phase")
            if phase not in projects_dict:
                projects_dict[phase] = {
                    "name": phase,
                    "description": f"{scenario_name} - {phase}",
                    "priority": "medium",
                    "category": "other",
                    "depends_on": [],
                    "deliverables": [],
                    "estimated_effort": "M",
                    "tasks": [],
                }
            task = {
                "title": step.get("title") or step.get("name", "Task"),
                "description": step.get("description", ""),
                "capability_tags": step.get("capability_tags", []),
                "acceptance_criteria": step.get("acceptance_criteria", ""),
                "priority": step.get("priority", "medium"),
                "depends_on": step.get("depends_on", []),
            }
            projects_dict[phase].setdefault("tasks", []).append(task)
            # 收集 deliverables
            if step.get("deliverable"):
                projects_dict[phase]["deliverables"].append(step["deliverable"])

        return list(projects_dict.values())

    def _try_parse_json(self, value: Optional[str]) -> Optional[Dict[str, Any]]:
        """安全解析 JSON"""
        if not value:
            return None
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    def _parse_context_md(self, context_md: str) -> List[Dict[str, Any]]:
        """从 context_md markdown 解析项目结构（简单实现）"""
        projects: List[Dict[str, Any]] = []
        current_project: Optional[Dict[str, Any]] = None
        lines = context_md.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") and "project" in line.lower():
                if current_project:
                    projects.append(current_project)
                # 提取标题: ## Project: xxx 或 ## xxx
                title = line.lstrip("#").strip()
                title = title.replace("Project:", "").strip()
                current_project = {
                    "name": title or "Implied Project",
                    "description": "",
                    "priority": "medium",
                    "category": "other",
                    "depends_on": [],
                    "deliverables": [],
                    "estimated_effort": "M",
                    "tasks": [],
                }
            elif line.startswith("- [ ] ") or line.startswith("- [x] "):
                task_title = line[6:].strip().lstrip("- ").strip()
                if current_project is None:
                    current_project = self._create_singleton_project("Implied Project", "")[0]
                current_project.setdefault("tasks", []).append({
                    "title": task_title,
                    "description": "",
                    "priority": "medium",
                    "depends_on": [],
                })
            elif line.startswith("**") and "**" in line[2:]:
                # Bold heading-like line could be description
                if current_project and not current_project["description"]:
                    current_project["description"] = line.strip("* ").strip()

        if current_project:
            projects.append(current_project)

        return projects

    def _create_singleton_project(
        self,
        title: str,
        description: str,
    ) -> List[Dict[str, Any]]:
        """创建单一默认项目（最终 fallback）"""
        return [{
            "name": title or "Default Project",
            "description": description or "",
            "priority": "medium",
            "category": "other",
            "depends_on": [],
            "deliverables": ["交付物 1"],
            "estimated_effort": "M",
        }]

    def apply_fallback_to_planning_session(
        self,
        planning_session_id: str,
        projects: List[Dict[str, Any]],
        assumptions: List[str],
    ) -> None:
        """将 fallback 结果写入 planning_session.confirmed_plan"""
        from models.planning_session import PlanningSession

        planning = self.db.query(PlanningSession).filter(
            PlanningSession.id == planning_session_id
        ).first()
        if not planning:
            logger.warning(
                f"[decomposition_fallback] PlanningSession {planning_session_id} not found"
            )
            return

        confirmed_plan = {
            "projects": projects,
            "assumptions": assumptions,
            "source": "default_fallback",
        }
        planning.confirmed_plan = json.dumps(confirmed_plan, ensure_ascii=False)
        planning.status = "confirmed"
        self.db.commit()

        logger.info(
            f"[decomposition_fallback] Applied fallback to planning_session "
            f"{planning_session_id}: {len(projects)} projects"
        )


# ---------------------------------------------------------------------------
# Standalone convenience function
# ---------------------------------------------------------------------------

def get_default_decomposition(db: Session, goal_id: str) -> Dict[str, Any]:
    """
    便捷函数：从 goal_id 获取默认分解结果。

    Returns:
        {
            "projects": [...],
            "assumptions": [...],
            "default_applied": bool,
        }
    """
    fallback = DecompositionFallback(db)
    projects, assumptions = fallback.extract_default_decomposition(goal_id)
    return {
        "projects": projects,
        "assumptions": assumptions,
        "default_applied": True,
    }
