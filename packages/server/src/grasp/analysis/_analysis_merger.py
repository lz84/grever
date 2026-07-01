"""Grasp 综合研判 — StepMerger（步骤合并器）"""
import uuid
from typing import List, Dict, Any

from ._analysis_models import TaskStep, PlanApplicability, MergedPlan, StepConflict, ConflictType


class StepMerger:
    """步骤合并器 — 去重、冲突检测、阶段生成。"""

    def __init__(self):
        self._step_name_synonyms = {
            '生命搜救': ['人员搜救', '搜救', '生命探测'],
            '建筑评估': ['结构评估', '建筑安全评估', '结构安全评估'],
            '医疗救援': ['医疗点设立', '临时医疗点', '医疗救治'],
            '通信恢复': ['通信保障', '应急通信', '通信系统恢复'],
            '人员安置': ['受灾人员安置', '避难所设置', '群众安置'],
            '次生灾害监测': ['次生灾害防范', '余震监测', '灾害监测'],
            '道路疏通': ['生命通道建立', '主干道清理', '道路清理'],
        }

    def merge_steps(
        self, plan_applicabilities: List[PlanApplicability], min_score: float = 0.2
    ) -> MergedPlan:
        """合并多个预案的核心步骤。"""
        applicable = [pa for pa in plan_applicabilities if pa.applicability_score >= min_score]
        if not applicable:
            return MergedPlan(merged_id=f"merged-{uuid.uuid4().hex[:8]}",
                              title="无适用预案", description="没有找到适用的预案", source_plans=[])

        all_tasks = []
        source_plan_ids = []
        for pa in applicable:
            source_plan_ids.append(pa.plan.plan_id)
            for task in pa.applicable_tasks:
                all_tasks.append(self._task_to_step(task, pa.plan.plan_id, pa.plan.title))

        merged_steps = self._deduplicate_steps(all_tasks)
        conflicts = self._detect_conflicts(merged_steps)
        phases = self._generate_phases(merged_steps)
        resource_summary = self._summarize_resources(merged_steps)
        title = f"综合研判预案（{len(applicable)}个预案合并）"
        description = f"基于{len(applicable)}个适用预案合并生成，共{len(merged_steps)}个核心步骤"

        return MergedPlan(
            merged_id=f"merged-{uuid.uuid4().hex[:8]}", title=title, description=description,
            source_plans=source_plan_ids, merged_steps=merged_steps, conflicts=conflicts,
            resource_summary=resource_summary, execution_phases=phases,
        )

    @staticmethod
    def _task_to_step(task: Dict[str, Any], plan_id: str, plan_name: str) -> TaskStep:
        """将预案任务转换为步骤。"""
        return TaskStep(
            step_id=task.get('taskId', f"step-{uuid.uuid4().hex[:8]}"),
            name=task.get('name', ''), description=task.get('description', ''),
            priority=task.get('priority', 'P1'), source_plan_id=plan_id, source_plan_name=plan_name,
            estimated_duration=task.get('estimatedDuration', ''),
            dependencies=task.get('dependencies', []), required_resources={},
            assigned_agents=task.get('assignedAgents', []),
        )

    def _deduplicate_steps(self, steps: List[TaskStep]) -> List[TaskStep]:
        """去重相似步骤，保留最高优先级版本。"""
        if not steps:
            return []
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        steps.sort(key=lambda s: priority_order.get(s.priority, 3))
        merged, used_names = [], set()
        for step in steps:
            canonical = self._get_canonical_name(step.name)
            if canonical in used_names:
                continue
            used_names.add(canonical)
            for canonical_name, synonyms in self._step_name_synonyms.items():
                if step.name in synonyms:
                    step.name = canonical_name
                    break
            merged.append(step)
        merged.sort(key=lambda s: priority_order.get(s.priority, 3))
        return merged

    def _get_canonical_name(self, name: str) -> str:
        """获取步骤名的规范化名称。"""
        for canonical, synonyms in self._step_name_synonyms.items():
            if name == canonical or name in synonyms:
                return canonical
        return name

    def _detect_conflicts(self, steps: List[TaskStep]) -> List[StepConflict]:
        """检测步骤之间的冲突。"""
        conflicts = []
        # 资源冲突
        resource_map: Dict[str, List[TaskStep]] = {}
        for step in steps:
            for agent in step.assigned_agents:
                resource_map.setdefault(agent, []).append(step)
        for agent, agent_steps in resource_map.items():
            if len(agent_steps) > 1:
                conflicts.append(StepConflict(
                    conflict_type=ConflictType.RESOURCE_CONFLICT,
                    steps=[s.step_id for s in agent_steps],
                    description=f"Agent '{agent}' 被分配到多个步骤: {', '.join(s.name for s in agent_steps)}",
                    severity="medium", resolution=f"建议调整执行顺序或增加'{agent}'资源",
                ))
        # 依赖冲突
        step_ids = {s.step_id for s in steps}
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    conflicts.append(StepConflict(
                        conflict_type=ConflictType.LOGICAL_CONFLICT, steps=[step.step_id],
                        description=f"步骤 '{step.name}' 依赖 '{dep}'，但该步骤不在合并预案中",
                        severity="high", resolution="需要确认依赖步骤是否已完成或从其他预案引入",
                    ))
        # 优先级冲突
        p0_steps = [s for s in steps if s.priority == 'P0']
        if len(p0_steps) > 3:
            conflicts.append(StepConflict(
                conflict_type=ConflictType.PRIORITY_CONFLICT, steps=[s.step_id for s in p0_steps],
                description=f"存在{len(p0_steps)}个 P0 优先级步骤，资源可能不足",
                severity="high", resolution="建议重新评估 P0 步骤的优先级，确保关键任务优先执行",
            ))
        return conflicts

    def _generate_phases(self, steps: List[TaskStep]) -> List[Dict[str, Any]]:
        """生成执行阶段。"""
        phases = []
        priority_groups: Dict[str, List[TaskStep]] = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
        for step in steps:
            p = step.priority if step.priority in priority_groups else 'P2'
            priority_groups[p].append(step)
        phase_defs = [
            ('紧急响应阶段', '0-24h', 'P0 核心任务', 'P0'),
            ('全面执行阶段', '24h-72h', 'P1 重要任务', 'P1'),
            ('持续支持阶段', '72h-7天', 'P2 支持任务', 'P2'),
            ('优化阶段', '7天+', 'P3 优化任务', 'P3'),
        ]
        for phase_name, duration, focus, key in phase_defs:
            group = priority_groups[key]
            if group:
                phases.append({
                    'phase': phase_name, 'duration': duration, 'focus': focus,
                    'steps': [{'step_id': s.step_id, 'name': s.name} for s in group],
                    'step_count': len(group),
                })
        return phases

    @staticmethod
    def _summarize_resources(steps: List[TaskStep]) -> Dict[str, Any]:
        """汇总资源需求。"""
        unique_agents: set = set()
        for step in steps:
            for agent in step.assigned_agents:
                unique_agents.add(agent)
        return {'total_steps': len(steps), 'unique_agents': list(unique_agents), 'agent_count': len(unique_agents)}
