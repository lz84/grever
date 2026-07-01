"""Grasp 综合研判服务

分析多个预案的适用性，合并核心步骤，生成研判报告。

核心功能：
1. 多预案适用性分析 - 根据输入场景分析多个预案的适用程度
2. 核心步骤合并 - 从多个匹配预案中提取并合并核心步骤
3. 冲突检测 - 检测不同预案步骤之间的资源冲突和时间冲突
4. 综合研判报告 - 生成完整的研判报告，包含优先级、资源需求、执行时序
"""
from typing import List, Dict, Any, Optional

from .plans import PlanStore, PlanMatcher, get_store, get_matcher
from ._analysis_models import (
    ApplicabilityLevel, ConflictType, StepPriority,
    TaskStep, PlanApplicability, StepConflict, MergedPlan, AnalysisReport,
)
from ._analysis_analyzer import PlanAnalyzer
from ._analysis_merger import StepMerger
from ._analysis_report import AnalysisReportGenerator


class GraspAnalysisService:
    """Grasp 综合研判服务（统一入口）"""

    def __init__(self, store: Optional[PlanStore] = None,
                 matcher: Optional[PlanMatcher] = None, data_dir: Optional[str] = None):
        self._store = store or get_store(data_dir)
        self._matcher = matcher or get_matcher(data_dir)
        self._analyzer = PlanAnalyzer(self._store, self._matcher)
        self._merger = StepMerger()
        self._report_generator = AnalysisReportGenerator()

    def comprehensive_analysis(
        self, query: str, context: Optional[Dict[str, Any]] = None,
        limit: int = 10, min_merge_score: float = 0.2, generate_report: bool = True
    ) -> Dict[str, Any]:
        """综合研判分析（主入口方法）。"""
        plan_applicabilities = self._analyzer.analyze_applicability(query, context, limit)
        if not plan_applicabilities:
            return {'status': 'no_match', 'message': f'未找到与"{query}"匹配的预案',
                    'plan_applicabilities': [], 'merged_plan': None, 'report': None}
        merged_plan = self._merger.merge_steps(plan_applicabilities, min_merge_score)
        report = None
        if generate_report:
            report = self._report_generator.generate_report(query, plan_applicabilities, merged_plan)
        return {
            'status': 'success', 'query': query,
            'plan_applicabilities': [pa.to_dict() for pa in plan_applicabilities],
            'merged_plan': merged_plan.to_dict(),
            'report': report.to_dict() if report else None,
        }

    def analyze_applicability(self, query: str, context: Optional[Dict[str, Any]] = None,
                              limit: int = 10) -> List[PlanApplicability]:
        """仅分析适用性。"""
        return self._analyzer.analyze_applicability(query, context, limit)

    def merge_steps(self, plan_applicabilities: List[PlanApplicability],
                    min_score: float = 0.2) -> MergedPlan:
        """仅合并步骤。"""
        return self._merger.merge_steps(plan_applicabilities, min_score)

    def generate_report(self, query: str, plan_applicabilities: List[PlanApplicability],
                        merged_plan: Optional[MergedPlan] = None) -> AnalysisReport:
        """仅生成报告。"""
        return self._report_generator.generate_report(query, plan_applicabilities, merged_plan)


_default_service: Optional[GraspAnalysisService] = None


def get_analysis_service(data_dir: Optional[str] = None) -> GraspAnalysisService:
    """获取或创建全局 GraspAnalysisService"""
    global _default_service
    if _default_service is None:
        _default_service = GraspAnalysisService(data_dir=data_dir)
    return _default_service
