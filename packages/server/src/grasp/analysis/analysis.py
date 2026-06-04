"""
Grasp 综合研判服务

分析多个预案的适用性，合并核心步骤，生成研判报告。

核心功能：
1. 多预案适用性分析 - 根据输入场景分析多个预案的适用程度
2. 核心步骤合并 - 从多个匹配预案中提取并合并核心步骤
3. 冲突检测 - 检测不同预案步骤之间的资源冲突和时间冲突
4. 综合研判报告 - 生成完整的研判报告，包含优先级、资源需求、执行时序
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .plans import Plan, PlanStore, PlanMatcher, PlanMatchResult, get_store, get_matcher


# ==================== 数据类型定义 ====================

class ApplicabilityLevel(Enum):
    """适用性等级"""
    HIGHLY_APPLICABLE = "高度适用"       # 预案非常匹配当前场景
    PARTIALLY_APPLICABLE = "部分适用"    # 预案部分匹配，需要调整
    LOW_APPLICABILITY = "低适用"         # 预案不太匹配，仅供参考
    NOT_APPLICABLE = "不适用"            # 预案不适用


class ConflictType(Enum):
    """冲突类型"""
    RESOURCE_CONFLICT = "资源冲突"       # 多个步骤争夺同一资源
    TIME_CONFLICT = "时间冲突"           # 步骤时间窗口重叠
    PRIORITY_CONFLICT = "优先级冲突"     # 步骤优先级矛盾
    LOGICAL_CONFLICT = "逻辑冲突"        # 步骤逻辑矛盾


class StepPriority(Enum):
    """步骤优先级"""
    P0 = "P0"  # 最高优先级，立即执行
    P1 = "P1"  # 高优先级，尽快执行
    P2 = "P2"  # 中优先级，按计划执行
    P3 = "P3"  # 低优先级，可选执行


@dataclass
class TaskStep:
    """任务步骤"""
    step_id: str
    name: str
    description: str
    priority: str = "P1"
    source_plan_id: str = ""
    source_plan_name: str = ""
    estimated_duration: str = ""
    dependencies: List[str] = field(default_factory=list)
    required_resources: Dict[str, Any] = field(default_factory=dict)
    assigned_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanApplicability:
    """预案适用性分析结果"""
    plan: Plan
    applicability_level: ApplicabilityLevel
    applicability_score: float  # 0-1
    applicable_tasks: List[Dict[str, Any]] = field(default_factory=list)
    inapplicable_tasks: List[Dict[str, Any]] = field(default_factory=list)
    adaptation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan': self.plan.to_dict(),
            'applicability_level': self.applicability_level.value,
            'applicability_score': round(self.applicability_score, 4),
            'applicable_tasks': self.applicable_tasks,
            'inapplicable_tasks': self.inapplicable_tasks,
            'adaptation_notes': self.adaptation_notes,
        }


@dataclass
class StepConflict:
    """步骤冲突"""
    conflict_type: ConflictType
    steps: List[str]  # step_ids
    description: str
    severity: str = "medium"  # low, medium, high, critical
    resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MergedPlan:
    """合并后的综合预案"""
    merged_id: str
    title: str
    description: str
    source_plans: List[str]  # plan_ids
    merged_steps: List[TaskStep] = field(default_factory=list)
    conflicts: List[StepConflict] = field(default_factory=list)
    resource_summary: Dict[str, Any] = field(default_factory=dict)
    execution_phases: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'merged_id': self.merged_id,
            'title': self.title,
            'description': self.description,
            'source_plans': self.source_plans,
            'merged_steps': [s.to_dict() for s in self.merged_steps],
            'conflicts': [c.to_dict() for c in self.conflicts],
            'resource_summary': self.resource_summary,
            'execution_phases': self.execution_phases,
            'created_at': self.created_at,
        }


@dataclass
class AnalysisReport:
    """综合研判报告"""
    report_id: str
    query: str
    timestamp: str
    plan_applicabilities: List[PlanApplicability] = field(default_factory=list)
    merged_plan: Optional[MergedPlan] = None
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    risk_assessment: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'query': self.query,
            'timestamp': self.timestamp,
            'plan_applicabilities': [pa.to_dict() for pa in self.plan_applicabilities],
            'merged_plan': self.merged_plan.to_dict() if self.merged_plan else None,
            'summary': self.summary,
            'recommendations': self.recommendations,
            'risk_assessment': self.risk_assessment,
        }


# ==================== 核心服务类 ====================

class PlanAnalyzer:
    """
    预案适用性分析器

    分析多个预案对当前场景的适用程度，包括：
    - 任务适用性评估
    - 资源适配性检查
    - 场景匹配度计算
    """

    def __init__(self, store: PlanStore, matcher: PlanMatcher):
        self._store = store
        self._matcher = matcher

    def analyze_applicability(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[PlanApplicability]:
        """
        分析预案适用性

        :param query: 场景描述/关键词
        :param context: 额外上下文（如灾害类型、严重程度、可用资源等）
        :param limit: 返回数量上限
        :return: 按适用性评分降序排列的分析结果列表
        """
        # 1. 获取匹配的预案
        matched = self._matcher.search(query, limit=limit)
        if not matched:
            return []

        # 2. 对每个预案进行适用性分析
        results = []
        for match in matched:
            applicability = self._analyze_single_plan(match, context)
            results.append(applicability)

        # 3. 按适用性评分降序排序
        results.sort(key=lambda r: r.applicability_score, reverse=True)
        return results

    def _analyze_single_plan(
        self,
        match: PlanMatchResult,
        context: Optional[Dict[str, Any]] = None
    ) -> PlanApplicability:
        """分析单个预案的适用性"""
        plan = match.plan
        score = match.score

        # 解析预案内容（支持 JSON 和 Markdown 格式）
        plan_data = self._parse_plan_content(plan)
        tasks = plan_data.get('tasks', [])

        # 根据匹配分数确定适用性等级
        if score >= 0.7:
            level = ApplicabilityLevel.HIGHLY_APPLICABLE
        elif score >= 0.4:
            level = ApplicabilityLevel.PARTIALLY_APPLICABLE
        elif score >= 0.2:
            level = ApplicabilityLevel.LOW_APPLICABILITY
        else:
            level = ApplicabilityLevel.NOT_APPLICABLE

        # 考虑上下文调整评分
        if context:
            score = self._adjust_score_with_context(score, plan_data, context)
            level = self._score_to_level(score)

        # 分类任务为适用/不适用
        applicable_tasks = []
        inapplicable_tasks = []
        for task in tasks:
            if self._is_task_applicable(task, context):
                applicable_tasks.append(task)
            else:
                inapplicable_tasks.append(task)

        # 生成适配建议
        adaptation_notes = self._generate_adaptation_notes(plan_data, context, score)

        return PlanApplicability(
            plan=plan,
            applicability_level=level,
            applicability_score=min(score, 1.0),
            applicable_tasks=applicable_tasks,
            inapplicable_tasks=inapplicable_tasks,
            adaptation_notes=adaptation_notes,
        )

    def _parse_plan_content(self, plan: Plan) -> Dict[str, Any]:
        """解析预案内容（JSON 或 Markdown）"""
        content = plan.content.strip()

        # 尝试解析 JSON
        if content.startswith('{'):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

        # 尝试从 demo-data 加载对应的 JSON 文件
        plan_id = plan.plan_id
        demo_dir = Path(__file__).parent.parent / "demo-data"
        if demo_dir.exists():
            # 根据 plan_id 查找对应的 JSON 文件
            for json_file in demo_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('id') == plan_id:
                            return data
                except (json.JSONDecodeError, KeyError):
                    continue

        # 默认返回空结构
        return {'tasks': [], 'resources': {}, 'phases': []}

    def _adjust_score_with_context(
        self,
        base_score: float,
        plan_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """根据上下文调整适用性评分"""
        score = base_score

        # 灾害类型匹配
        disaster_type = context.get('disaster_type')
        plan_disaster_type = plan_data.get('disasterType') or plan_data.get('disaster_type')
        if disaster_type and plan_disaster_type:
            if disaster_type == plan_disaster_type:
                score = min(score + 0.15, 1.0)
            elif disaster_type in plan_disaster_type or plan_disaster_type in disaster_type:
                score = min(score + 0.08, 1.0)

        # 响应级别匹配
        response_level = context.get('response_level')
        plan_response_level = plan_data.get('responseLevel') or plan_data.get('response_level')
        if response_level and plan_response_level:
            if response_level == plan_response_level:
                score = min(score + 0.1, 1.0)

        # 可用资源检查
        available_resources = context.get('available_resources')
        if available_resources and plan_data.get('resources'):
            required = plan_data['resources']
            match_ratio = self._calculate_resource_match_ratio(available_resources, required)
            score = score * (0.7 + 0.3 * match_ratio)  # 资源不匹配时降低评分

        return score

    def _calculate_resource_match_ratio(
        self,
        available: Dict[str, Any],
        required: Dict[str, Any]
    ) -> float:
        """计算资源匹配比例"""
        if not required:
            return 1.0

        total_required = 0
        total_available = 0

        # 检查人员
        req_personnel = required.get('personnel', {})
        avail_personnel = available.get('personnel', {})
        for category, req_info in req_personnel.items():
            req_count = req_info.get('count', 0) if isinstance(req_info, dict) else 0
            avail_count = avail_personnel.get(category, {}).get('count', 0) if isinstance(avail_personnel.get(category), dict) else 0
            total_required += req_count
            total_available += min(avail_count, req_count)

        if total_required == 0:
            return 1.0

        return total_available / total_required

    def _is_task_applicable(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """判断任务是否适用于当前场景"""
        if not context:
            return True

        # 检查任务优先级是否在可接受范围内
        min_priority = context.get('min_priority')
        if min_priority:
            task_priority = task.get('priority', 'P3')
            priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
            if priority_order.get(task_priority, 3) > priority_order.get(min_priority, 3):
                return False

        return True

    def _generate_adaptation_notes(
        self,
        plan_data: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        score: float
    ) -> str:
        """生成适配建议"""
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

    def _score_to_level(self, score: float) -> ApplicabilityLevel:
        """将分数转换为适用性等级"""
        if score >= 0.7:
            return ApplicabilityLevel.HIGHLY_APPLICABLE
        elif score >= 0.4:
            return ApplicabilityLevel.PARTIALLY_APPLICABLE
        elif score >= 0.2:
            return ApplicabilityLevel.LOW_APPLICABILITY
        else:
            return ApplicabilityLevel.NOT_APPLICABLE


class StepMerger:
    """
    步骤合并器

    从多个预案中提取核心步骤，合并为统一的执行计划：
    - 去重相似步骤
    - 统一优先级
    - 检测资源冲突
    - 生成执行阶段
    """

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
        self,
        plan_applicabilities: List[PlanApplicability],
        min_score: float = 0.2
    ) -> MergedPlan:
        """
        合并多个预案的核心步骤

        :param plan_applicabilities: 预案适用性分析结果
        :param min_score: 最低适用性评分阈值
        :return: 合并后的综合预案
        """
        # 过滤掉适用性太低的预案
        applicable = [
            pa for pa in plan_applicabilities
            if pa.applicability_score >= min_score
        ]

        if not applicable:
            return MergedPlan(
                merged_id=f"merged-{uuid.uuid4().hex[:8]}",
                title="无适用预案",
                description="没有找到适用的预案",
                source_plans=[],
            )

        # 收集所有适用的任务
        all_tasks = []
        source_plan_ids = []
        for pa in applicable:
            source_plan_ids.append(pa.plan.plan_id)
            for task in pa.applicable_tasks:
                task_step = self._task_to_step(task, pa.plan.plan_id, pa.plan.title)
                all_tasks.append(task_step)

        # 去重和合并相似步骤
        merged_steps = self._deduplicate_steps(all_tasks)

        # 检测冲突
        conflicts = self._detect_conflicts(merged_steps)

        # 生成执行阶段
        phases = self._generate_phases(merged_steps)

        # 汇总资源需求
        resource_summary = self._summarize_resources(merged_steps)

        # 生成标题和描述
        title = f"综合研判预案（{len(applicable)}个预案合并）"
        description = f"基于{len(applicable)}个适用预案合并生成，共{len(merged_steps)}个核心步骤"

        return MergedPlan(
            merged_id=f"merged-{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            source_plans=source_plan_ids,
            merged_steps=merged_steps,
            conflicts=conflicts,
            resource_summary=resource_summary,
            execution_phases=phases,
        )

    def _task_to_step(self, task: Dict[str, Any], plan_id: str, plan_name: str) -> TaskStep:
        """将预案任务转换为步骤"""
        return TaskStep(
            step_id=task.get('taskId', f"step-{uuid.uuid4().hex[:8]}"),
            name=task.get('name', ''),
            description=task.get('description', ''),
            priority=task.get('priority', 'P1'),
            source_plan_id=plan_id,
            source_plan_name=plan_name,
            estimated_duration=task.get('estimatedDuration', ''),
            dependencies=task.get('dependencies', []),
            required_resources={},
            assigned_agents=task.get('assignedAgents', []),
        )

    def _deduplicate_steps(self, steps: List[TaskStep]) -> List[TaskStep]:
        """去重相似步骤，保留最高优先级的版本"""
        if not steps:
            return []

        # 按优先级排序
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        steps.sort(key=lambda s: priority_order.get(s.priority, 3))

        merged = []
        used_names = set()

        for step in steps:
            canonical_name = self._get_canonical_name(step.name)

            if canonical_name in used_names:
                # 已存在相似步骤，跳过（保留优先级更高的）
                continue

            used_names.add(canonical_name)

            # 如果步骤名被同义词映射，更新步骤名
            for canonical, synonyms in self._step_name_synonyms.items():
                if step.name in synonyms:
                    step.name = canonical
                    break

            merged.append(step)

        # 重新按优先级排序
        merged.sort(key=lambda s: priority_order.get(s.priority, 3))
        return merged

    def _get_canonical_name(self, name: str) -> str:
        """获取步骤名的规范化名称"""
        for canonical, synonyms in self._step_name_synonyms.items():
            if name == canonical or name in synonyms:
                return canonical
        return name

    def _detect_conflicts(self, steps: List[TaskStep]) -> List[StepConflict]:
        """检测步骤之间的冲突"""
        conflicts = []

        # 1. 资源冲突检测
        resource_map: Dict[str, List[TaskStep]] = {}
        for step in steps:
            for agent in step.assigned_agents:
                if agent not in resource_map:
                    resource_map[agent] = []
                resource_map[agent].append(step)

        for agent, agent_steps in resource_map.items():
            if len(agent_steps) > 1:
                # 检查是否有时间重叠
                conflicting_steps = [s.step_id for s in agent_steps]
                conflicts.append(StepConflict(
                    conflict_type=ConflictType.RESOURCE_CONFLICT,
                    steps=conflicting_steps,
                    description=f"Agent '{agent}' 被分配到多个步骤: {', '.join(s.name for s in agent_steps)}",
                    severity="medium",
                    resolution=f"建议调整执行顺序或增加'{agent}'资源",
                ))

        # 2. 依赖冲突检测
        step_ids = {s.step_id for s in steps}
        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    conflicts.append(StepConflict(
                        conflict_type=ConflictType.LOGICAL_CONFLICT,
                        steps=[step.step_id],
                        description=f"步骤 '{step.name}' 依赖 '{dep}'，但该步骤不在合并预案中",
                        severity="high",
                        resolution=f"需要确认依赖步骤是否已完成或从其他预案引入",
                    ))

        # 3. 优先级冲突检测（P0 步骤有多个时）
        p0_steps = [s for s in steps if s.priority == 'P0']
        if len(p0_steps) > 3:
            conflicts.append(StepConflict(
                conflict_type=ConflictType.PRIORITY_CONFLICT,
                steps=[s.step_id for s in p0_steps],
                description=f"存在{len(p0_steps)}个 P0 优先级步骤，资源可能不足",
                severity="high",
                resolution="建议重新评估 P0 步骤的优先级，确保关键任务优先执行",
            ))

        return conflicts

    def _generate_phases(self, steps: List[TaskStep]) -> List[Dict[str, Any]]:
        """生成执行阶段"""
        phases = []

        # 按优先级分组
        priority_groups = {'P0': [], 'P1': [], 'P2': [], 'P3': []}
        for step in steps:
            p = step.priority if step.priority in priority_groups else 'P2'
            priority_groups[p].append(step)

        # P0 阶段：黄金救援
        if priority_groups['P0']:
            phases.append({
                'phase': '紧急响应阶段',
                'duration': '0-24h',
                'focus': 'P0 核心任务',
                'steps': [{'step_id': s.step_id, 'name': s.name} for s in priority_groups['P0']],
                'step_count': len(priority_groups['P0']),
            })

        # P1 阶段：全面救援
        if priority_groups['P1']:
            phases.append({
                'phase': '全面执行阶段',
                'duration': '24h-72h',
                'focus': 'P1 重要任务',
                'steps': [{'step_id': s.step_id, 'name': s.name} for s in priority_groups['P1']],
                'step_count': len(priority_groups['P1']),
            })

        # P2 阶段：持续支持
        if priority_groups['P2']:
            phases.append({
                'phase': '持续支持阶段',
                'duration': '72h-7天',
                'focus': 'P2 支持任务',
                'steps': [{'step_id': s.step_id, 'name': s.name} for s in priority_groups['P2']],
                'step_count': len(priority_groups['P2']),
            })

        # P3 阶段：可选任务
        if priority_groups['P3']:
            phases.append({
                'phase': '优化阶段',
                'duration': '7天+',
                'focus': 'P3 优化任务',
                'steps': [{'step_id': s.step_id, 'name': s.name} for s in priority_groups['P3']],
                'step_count': len(priority_groups['P3']),
            })

        return phases

    def _summarize_resources(self, steps: List[TaskStep]) -> Dict[str, Any]:
        """汇总资源需求"""
        resource_summary = {
            'total_steps': len(steps),
            'unique_agents': set(),
            'agent_count': 0,
        }

        for step in steps:
            for agent in step.assigned_agents:
                resource_summary['unique_agents'].add(agent)

        resource_summary['agent_count'] = len(resource_summary['unique_agents'])
        resource_summary['unique_agents'] = list(resource_summary['unique_agents'])

        return resource_summary


class AnalysisReportGenerator:
    """
    研判报告生成器

    生成完整的综合研判报告，包含：
    - 预案适用性分析摘要
    - 合并后的执行计划
    - 风险评估
    - 行动建议
    """

    def generate_report(
        self,
        query: str,
        plan_applicabilities: List[PlanApplicability],
        merged_plan: Optional[MergedPlan] = None
    ) -> AnalysisReport:
        """
        生成综合研判报告

        :param query: 原始查询
        :param plan_applicabilities: 预案适用性分析结果
        :param merged_plan: 合并后的综合预案
        :return: 完整的研判报告
        """
        report_id = f"report-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        # 生成摘要
        summary = self._generate_summary(query, plan_applicabilities, merged_plan)

        # 生成建议
        recommendations = self._generate_recommendations(plan_applicabilities, merged_plan)

        # 风险评估
        risk_assessment = self._generate_risk_assessment(plan_applicabilities, merged_plan)

        return AnalysisReport(
            report_id=report_id,
            query=query,
            timestamp=timestamp,
            plan_applicabilities=plan_applicabilities,
            merged_plan=merged_plan,
            summary=summary,
            recommendations=recommendations,
            risk_assessment=risk_assessment,
        )

    def _generate_summary(
        self,
        query: str,
        plan_applicabilities: List[PlanApplicability],
        merged_plan: Optional[MergedPlan]
    ) -> str:
        """生成报告摘要"""
        lines = []
        lines.append(f"查询场景：{query}")
        lines.append(f"匹配预案数：{len(plan_applicabilities)}")

        highly_applicable = sum(
            1 for pa in plan_applicabilities
            if pa.applicability_level == ApplicabilityLevel.HIGHLY_APPLICABLE
        )
        partially_applicable = sum(
            1 for pa in plan_applicabilities
            if pa.applicability_level == ApplicabilityLevel.PARTIALLY_APPLICABLE
        )

        lines.append(f"高度适用：{highly_applicable}个")
        lines.append(f"部分适用：{partially_applicable}个")

        if merged_plan:
            lines.append(f"合并步骤数：{len(merged_plan.merged_steps)}")
            lines.append(f"检测到冲突数：{len(merged_plan.conflicts)}")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        plan_applicabilities: List[PlanApplicability],
        merged_plan: Optional[MergedPlan]
    ) -> List[str]:
        """生成行动建议"""
        recommendations = []

        if not plan_applicabilities:
            recommendations.append("未找到适用预案，建议人工研判或创建新预案")
            return recommendations

        # 基于适用性分析的建议
        best_match = plan_applicabilities[0]
        if best_match.applicability_score >= 0.7:
            recommendations.append(f"预案'{best_match.plan.title}'高度适用，建议作为主要参考")
        else:
            recommendations.append(f"预案'{best_match.plan.title}'部分适用，需根据实际情况调整")

        # 基于合并预案的建议
        if merged_plan:
            if merged_plan.conflicts:
                high_conflicts = [c for c in merged_plan.conflicts if c.severity in ('high', 'critical')]
                if high_conflicts:
                    recommendations.append(f"存在{len(high_conflicts)}个高严重度冲突，需优先解决")

            if len(merged_plan.merged_steps) > 10:
                recommendations.append("合并后步骤较多，建议分阶段执行，优先完成 P0 任务")

        # 通用建议
        recommendations.append("建议每 30 分钟评估一次执行进度，根据实际情况调整预案")
        recommendations.append("确保各 Agent 之间的通信畅通，及时同步执行状态")

        return recommendations

    def _generate_risk_assessment(
        self,
        plan_applicabilities: List[PlanApplicability],
        merged_plan: Optional[MergedPlan]
    ) -> List[str]:
        """生成风险评估"""
        risks = []

        # 预案适用性风险
        low_applicable = [
            pa for pa in plan_applicabilities
            if pa.applicability_level == ApplicabilityLevel.LOW_APPLICABILITY
        ]
        if low_applicable:
            risks.append(f"{len(low_applicable)}个预案适用性较低，直接使用可能导致执行偏差")

        # 资源风险
        if merged_plan:
            high_conflicts = [c for c in merged_plan.conflicts if c.severity == 'high']
            if high_conflicts:
                for conflict in high_conflicts:
                    risks.append(f"高风险：{conflict.description}")

            critical_conflicts = [c for c in merged_plan.conflicts if c.severity == 'critical']
            if critical_conflicts:
                risks.append(f"存在{len(critical_conflicts)}个严重冲突，必须解决后才能执行")

        # 通用风险
        if not risks:
            risks.append("风险评估：整体风险可控，按计划执行即可")

        return risks


# ==================== 统一入口 ====================

class GraspAnalysisService:
    """
    Grasp 综合研判服务（统一入口）

    整合 PlanAnalyzer、StepMerger、AnalysisReportGenerator，
    提供一站式的预案分析、步骤合并和报告生成能力。
    """

    def __init__(
        self,
        store: Optional[PlanStore] = None,
        matcher: Optional[PlanMatcher] = None,
        data_dir: Optional[str] = None
    ):
        self._store = store or get_store(data_dir)
        self._matcher = matcher or get_matcher(data_dir)
        self._analyzer = PlanAnalyzer(self._store, self._matcher)
        self._merger = StepMerger()
        self._report_generator = AnalysisReportGenerator()

    def comprehensive_analysis(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        min_merge_score: float = 0.2,
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """
        综合研判分析（主入口方法）

        :param query: 场景描述/查询关键词
        :param context: 额外上下文信息
            - disaster_type: 灾害类型
            - response_level: 响应级别
            - available_resources: 可用资源
            - min_priority: 最低优先级
        :param limit: 匹配预案数量上限
        :param min_merge_score: 最低合并评分阈值
        :param generate_report: 是否生成研判报告
        :return: 分析结果字典
        """
        # 1. 适用性分析
        plan_applicabilities = self._analyzer.analyze_applicability(
            query, context, limit
        )

        if not plan_applicabilities:
            return {
                'status': 'no_match',
                'message': f'未找到与"{query}"匹配的预案',
                'plan_applicabilities': [],
                'merged_plan': None,
                'report': None,
            }

        # 2. 步骤合并
        merged_plan = self._merger.merge_steps(plan_applicabilities, min_merge_score)

        # 3. 生成报告
        report = None
        if generate_report:
            report = self._report_generator.generate_report(
                query, plan_applicabilities, merged_plan
            )

        return {
            'status': 'success',
            'query': query,
            'plan_applicabilities': [pa.to_dict() for pa in plan_applicabilities],
            'merged_plan': merged_plan.to_dict(),
            'report': report.to_dict() if report else None,
        }

    def analyze_applicability(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[PlanApplicability]:
        """仅分析适用性"""
        return self._analyzer.analyze_applicability(query, context, limit)

    def merge_steps(
        self,
        plan_applicabilities: List[PlanApplicability],
        min_score: float = 0.2
    ) -> MergedPlan:
        """仅合并步骤"""
        return self._merger.merge_steps(plan_applicabilities, min_score)

    def generate_report(
        self,
        query: str,
        plan_applicabilities: List[PlanApplicability],
        merged_plan: Optional[MergedPlan] = None
    ) -> AnalysisReport:
        """仅生成报告"""
        return self._report_generator.generate_report(
            query, plan_applicabilities, merged_plan
        )


# ==================== 全局实例 ====================

_default_service: Optional[GraspAnalysisService] = None


def get_analysis_service(data_dir: Optional[str] = None) -> GraspAnalysisService:
    """获取或创建全局 GraspAnalysisService"""
    global _default_service
    if _default_service is None:
        _default_service = GraspAnalysisService(data_dir=data_dir)
    return _default_service
