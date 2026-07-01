"""Grasp 综合研判 — AnalysisReportGenerator（研判报告生成器）"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from ._analysis_models import PlanApplicability, MergedPlan, AnalysisReport, ApplicabilityLevel


class AnalysisReportGenerator:
    """研判报告生成器 — 生成综合研判报告。"""

    def generate_report(
        self, query: str, plan_applicabilities: List[PlanApplicability],
        merged_plan: Optional[MergedPlan] = None
    ) -> AnalysisReport:
        """生成综合研判报告。"""
        return AnalysisReport(
            report_id=f"report-{uuid.uuid4().hex[:8]}", query=query,
            timestamp=datetime.now().isoformat(),
            plan_applicabilities=plan_applicabilities, merged_plan=merged_plan,
            summary=self._generate_summary(query, plan_applicabilities, merged_plan),
            recommendations=self._generate_recommendations(plan_applicabilities, merged_plan),
            risk_assessment=self._generate_risk_assessment(plan_applicabilities, merged_plan),
        )

    @staticmethod
    def _generate_summary(query: str, plan_applicabilities: List[PlanApplicability],
                          merged_plan: Optional[MergedPlan]) -> str:
        """生成报告摘要。"""
        lines = [f"查询场景：{query}", f"匹配预案数：{len(plan_applicabilities)}"]
        highly = sum(1 for pa in plan_applicabilities if pa.applicability_level == ApplicabilityLevel.HIGHLY_APPLICABLE)
        partially = sum(1 for pa in plan_applicabilities if pa.applicability_level == ApplicabilityLevel.PARTIALLY_APPLICABLE)
        lines.extend([f"高度适用：{highly}个", f"部分适用：{partially}个"])
        if merged_plan:
            lines.extend([f"合并步骤数：{len(merged_plan.merged_steps)}", f"检测到冲突数：{len(merged_plan.conflicts)}"])
        return "\n".join(lines)

    def _generate_recommendations(self, plan_applicabilities: List[PlanApplicability],
                                  merged_plan: Optional[MergedPlan]) -> List[str]:
        """生成行动建议。"""
        recommendations = []
        if not plan_applicabilities:
            recommendations.append("未找到适用预案，建议人工研判或创建新预案")
            return recommendations
        best = plan_applicabilities[0]
        if best.applicability_score >= 0.7:
            recommendations.append(f"预案'{best.plan.title}'高度适用，建议作为主要参考")
        else:
            recommendations.append(f"预案'{best.plan.title}'部分适用，需根据实际情况调整")
        if merged_plan:
            high_conflicts = [c for c in merged_plan.conflicts if c.severity in ('high', 'critical')]
            if high_conflicts:
                recommendations.append(f"存在{len(high_conflicts)}个高严重度冲突，需优先解决")
            if len(merged_plan.merged_steps) > 10:
                recommendations.append("合并后步骤较多，建议分阶段执行，优先完成 P0 任务")
        recommendations.append("建议每 30 分钟评估一次执行进度，根据实际情况调整预案")
        recommendations.append("确保各 Agent 之间的通信畅通，及时同步执行状态")
        return recommendations

    def _generate_risk_assessment(self, plan_applicabilities: List[PlanApplicability],
                                  merged_plan: Optional[MergedPlan]) -> List[str]:
        """生成风险评估。"""
        risks = []
        low = [pa for pa in plan_applicabilities if pa.applicability_level == ApplicabilityLevel.LOW_APPLICABILITY]
        if low:
            risks.append(f"{len(low)}个预案适用性较低，直接使用可能导致执行偏差")
        if merged_plan:
            high_conflicts = [c for c in merged_plan.conflicts if c.severity == 'high']
            for conflict in high_conflicts:
                risks.append(f"高风险：{conflict.description}")
            critical_conflicts = [c for c in merged_plan.conflicts if c.severity == 'critical']
            if critical_conflicts:
                risks.append(f"存在{len(critical_conflicts)}个严重冲突，必须解决后才能执行")
        if not risks:
            risks.append("风险评估：整体风险可控，按计划执行即可")
        return risks
