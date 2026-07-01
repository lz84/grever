"""Grasp 综合研判 — PlanAnalyzer（预案适用性分析器）"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .plans import Plan, PlanStore, PlanMatcher, PlanMatchResult
from ._analysis_models import ApplicabilityLevel, PlanApplicability


class PlanAnalyzer:
    """预案适用性分析器"""

    def __init__(self, store: PlanStore, matcher: PlanMatcher):
        self._store = store
        self._matcher = matcher

    def analyze_applicability(
        self, query: str, context: Optional[Dict[str, Any]] = None, limit: int = 10
    ) -> List[PlanApplicability]:
        """分析预案适用性，按适用性评分降序返回。"""
        matched = self._matcher.search(query, limit=limit)
        if not matched:
            return []
        results = [self._analyze_single_plan(m, context) for m in matched]
        results.sort(key=lambda r: r.applicability_score, reverse=True)
        return results

    def _analyze_single_plan(
        self, match: PlanMatchResult, context: Optional[Dict[str, Any]] = None
    ) -> PlanApplicability:
        """分析单个预案的适用性。"""
        plan = match.plan
        score = match.score
        plan_data = self._parse_plan_content(plan)
        tasks = plan_data.get('tasks', [])

        level = self._score_to_level(score)
        if context:
            score = self._adjust_score_with_context(score, plan_data, context)
            level = self._score_to_level(score)

        applicable_tasks = [t for t in tasks if self._is_task_applicable(t, context)]
        inapplicable_tasks = [t for t in tasks if not self._is_task_applicable(t, context)]
        adaptation_notes = self._generate_adaptation_notes(plan_data, context, score)

        return PlanApplicability(
            plan=plan, applicability_level=level,
            applicability_score=min(score, 1.0),
            applicable_tasks=applicable_tasks, inapplicable_tasks=inapplicable_tasks,
            adaptation_notes=adaptation_notes,
        )

    def _parse_plan_content(self, plan: Plan) -> Dict[str, Any]:
        """解析预案内容（JSON 或 demo-data 文件）。"""
        content = plan.content.strip()
        if content.startswith('{'):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        plan_id = plan.plan_id
        demo_dir = Path(__file__).parent.parent / "demo-data"
        if demo_dir.exists():
            for json_file in demo_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('id') == plan_id:
                            return data
                except (json.JSONDecodeError, KeyError):
                    continue
        return {'tasks': [], 'resources': {}, 'phases': []}

    def _adjust_score_with_context(
        self, base_score: float, plan_data: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """根据上下文调整适用性评分。"""
        score = base_score
        disaster_type = context.get('disaster_type')
        plan_disaster_type = plan_data.get('disasterType') or plan_data.get('disaster_type')
        if disaster_type and plan_disaster_type:
            if disaster_type == plan_disaster_type:
                score = min(score + 0.15, 1.0)
            elif disaster_type in plan_disaster_type or plan_disaster_type in disaster_type:
                score = min(score + 0.08, 1.0)
        response_level = context.get('response_level')
        plan_response_level = plan_data.get('responseLevel') or plan_data.get('response_level')
        if response_level and plan_response_level and response_level == plan_response_level:
            score = min(score + 0.1, 1.0)
        available_resources = context.get('available_resources')
        if available_resources and plan_data.get('resources'):
            match_ratio = self._calculate_resource_match_ratio(available_resources, plan_data['resources'])
            score = score * (0.7 + 0.3 * match_ratio)
        return score

    @staticmethod
    def _calculate_resource_match_ratio(available: Dict[str, Any], required: Dict[str, Any]) -> float:
        """计算资源匹配比例。"""
        if not required:
            return 1.0
        total_required = 0
        total_available = 0
        req_personnel = required.get('personnel', {})
        avail_personnel = available.get('personnel', {})
        for category, req_info in req_personnel.items():
            req_count = req_info.get('count', 0) if isinstance(req_info, dict) else 0
            avail_count = avail_personnel.get(category, {}).get('count', 0) if isinstance(avail_personnel.get(category), dict) else 0
            total_required += req_count
            total_available += min(avail_count, req_count)
        return total_available / total_required if total_required else 1.0

    @staticmethod
    def _is_task_applicable(task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """判断任务是否适用于当前场景。"""
        if not context:
            return True
        min_priority = context.get('min_priority')
        if min_priority:
            task_priority = task.get('priority', 'P3')
            priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
            if priority_order.get(task_priority, 3) > priority_order.get(min_priority, 3):
                return False
        return True

    def _generate_adaptation_notes(
        self, plan_data: Dict[str, Any], context: Optional[Dict[str, Any]], score: float
    ) -> str:
        """生成适配建议。"""
        notes = []
        if score < 0.4:
            notes.append("预案匹配度较低，建议仅作为参考")
        if context:
            disaster_type = context.get('disaster_type')
            plan_type = plan_data.get('disasterType') or plan_data.get('disaster_type')
            if disaster_type and plan_type and disaster_type != plan_type:
                notes.append(f"预案针对'{plan_type}'场景，当前为'{disaster_type}'场景，需调整任务细节")
            available_resources = context.get('available_resources')
            if available_resources and plan_data.get('resources'):
                match_ratio = self._calculate_resource_match_ratio(available_resources, plan_data['resources'])
                if match_ratio < 0.7:
                    notes.append(f"资源匹配度{match_ratio:.0%}，可能需要补充资源或调整任务规模")
        if not notes:
            notes.append("预案适用性良好，可直接参考执行")
        return "；".join(notes)

    @staticmethod
    def _score_to_level(score: float) -> ApplicabilityLevel:
        """将分数转换为适用性等级。"""
        if score >= 0.7:
            return ApplicabilityLevel.HIGHLY_APPLICABLE
        elif score >= 0.4:
            return ApplicabilityLevel.PARTIALLY_APPLICABLE
        elif score >= 0.2:
            return ApplicabilityLevel.LOW_APPLICABILITY
        return ApplicabilityLevel.NOT_APPLICABLE
