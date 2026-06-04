"""
Evo - 突变分析器 (Analyzer)

分析变异结果，决定是否采纳。

分析维度：
- 性能提升/下降
- 稳定性变化
- 副作用检测
- 回滚建议
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from evo.mutation.mutation import Mutation, MutationResult, MutationType

logger = logging.getLogger(__name__)


class AdoptionDecision(str, Enum):
    """采纳决策"""
    ACCEPT = "accept"           # 采纳
    REJECT = "reject"           # 拒绝
    TRIAL = "trial"             # 试用（继续观察）
    ROLLBACK = "rollback"       # 回滚


@dataclass
class AnalysisReport:
    """分析报告"""
    mutation_id: str
    decision: AdoptionDecision
    score: float  # -1.0 ~ 1.0, 正面→负面
    metrics: Dict[str, float]
    reasoning: str
    recommendations: List[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "decision": self.decision.value,
            "score": self.score,
            "metrics": self.metrics,
            "reasoning": self.reasoning,
            "recommendations": self.recommendations,
        }


class MutationAnalyzer:
    """
    突变分析器

    用法：
        analyzer = MutationAnalyzer()
        result = analyzer.analyze(mutation, before_metrics, after_metrics)
    """

    # 决策阈值
    ACCEPT_THRESHOLD = 0.15       # score > 0.15 → 采纳
    REJECT_THRESHOLD = -0.15      # score < -0.15 → 拒绝
    TRIAL_PERIOD_TASKS = 10       # 试用期间最少观察任务数

    # 副作用检测阈值
    MAX_REGRESSION = -0.1         # 最大允许的回退幅度

    def __init__(self):
        self._reports: Dict[str, AnalysisReport] = {}
        self._mutation_results: Dict[str, MutationResult] = {}
        # 跟踪每个目标的突变历史
        self._target_history: Dict[str, List[AnalysisReport]] = {}

    def analyze(
        self,
        mutation: Mutation,
        before_metrics: Dict[str, float],
        after_metrics: Dict[str, float],
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisReport:
        """
        分析突变结果。

        Args:
            mutation: 突变对象
            before_metrics: 突变前的指标
            after_metrics: 突变后的指标
            context: 额外上下文

        Returns:
            分析报告
        """
        # 1. 计算性能变化
        performance_delta = self._compute_performance_delta(before_metrics, after_metrics)

        # 2. 检测副作用
        side_effects = self._detect_side_effects(before_metrics, after_metrics)

        # 3. 检查历史趋势
        trend = self._check_trend(mutation.target_id, performance_delta)

        # 4. 综合评分
        score = self._compute_score(performance_delta, side_effects, trend)

        # 5. 决策
        decision = self._make_decision(score, mutation, trend)

        # 6. 生成推理
        reasoning = self._generate_reasoning(decision, performance_delta, side_effects, trend)

        # 7. 生成建议
        recommendations = self._generate_recommendations(decision, mutation, performance_delta)

        report = AnalysisReport(
            mutation_id=mutation.mutation_id,
            decision=decision,
            score=round(score, 4),
            metrics={
                "performance_delta": performance_delta,
                "side_effects_count": len(side_effects),
                "trend_score": trend,
            },
            reasoning=reasoning,
            recommendations=recommendations,
        )

        self._reports[mutation.mutation_id] = report

        # 更新目标历史
        self._target_history.setdefault(mutation.target_id, []).append(report)

        # 创建突变结果
        result = MutationResult(
            mutation=mutation,
            applied=decision == AdoptionDecision.ACCEPT,
            outcome_score=score,
            evaluation_notes=reasoning,
            evaluated_at=datetime.now(),
        )
        self._mutation_results[mutation.mutation_id] = result

        logger.info(
            "Analysis for %s: decision=%s score=%.4f (%s)",
            mutation.mutation_id, decision.value, score, reasoning,
        )
        return report

    def get_report(self, mutation_id: str) -> Optional[AnalysisReport]:
        return self._reports.get(mutation_id)

    def get_target_history(self, target_id: str) -> List[AnalysisReport]:
        """获取目标的分析历史"""
        return self._target_history.get(target_id, [])

    def get_accepted_mutations(self) -> List[AnalysisReport]:
        """获取已采纳的突变"""
        return [r for r in self._reports.values() if r.decision == AdoptionDecision.ACCEPT]

    def get_rejected_mutations(self) -> List[AnalysisReport]:
        """获取已拒绝的突变"""
        return [r for r in self._reports.values() if r.decision == AdoptionDecision.REJECT]

    # ---------- 内部分析方法 ----------

    def _compute_performance_delta(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
    ) -> float:
        """
        计算综合性能变化。

        比较关键指标的变化：
        - success_rate: 成功率 (越高越好)
        - avg_quality: 平均质量 (越高越好)
        - avg_duration_ms: 平均时长 (越低越好)
        - error_rate: 错误率 (越低越好)
        """
        deltas = []

        # 成功率变化
        if "success_rate" in before and "success_rate" in after:
            delta = after["success_rate"] - before["success_rate"]
            deltas.append(delta)  # 正值 = 改善

        # 质量变化
        if "avg_quality" in before and "avg_quality" in after:
            delta = after["avg_quality"] - before["avg_quality"]
            deltas.append(delta)

        # 时长变化（反向：越低越好）
        if "avg_duration_ms" in before and "avg_duration_ms" in after:
            if before["avg_duration_ms"] > 0:
                delta = -(after["avg_duration_ms"] - before["avg_duration_ms"]) / before["avg_duration_ms"]
                deltas.append(delta)

        # 错误率变化（反向：越低越好）
        if "error_rate" in before and "error_rate" in after:
            delta = -(after["error_rate"] - before["error_rate"])
            deltas.append(delta)

        if not deltas:
            return 0.0

        return sum(deltas) / len(deltas)

    def _detect_side_effects(
        self,
        before: Dict[str, float],
        after: Dict[str, float],
    ) -> List[str]:
        """检测副作用"""
        effects = []

        # 检查是否有指标显著恶化
        for key in before:
            if key in after:
                if key in ("success_rate", "avg_quality"):
                    if after[key] < before[key] + self.MAX_REGRESSION:
                        effects.append(f"{key} degraded: {before[key]:.3f} -> {after[key]:.3f}")
                elif key in ("avg_duration_ms", "error_rate"):
                    if after[key] > before[key] * (1 - self.MAX_REGRESSION):
                        effects.append(f"{key} increased: {before[key]:.3f} -> {after[key]:.3f}")

        return effects

    def _check_trend(self, target_id: str, current_delta: float) -> float:
        """检查目标的历史趋势"""
        history = self._target_history.get(target_id, [])
        if not history:
            return 0.0

        recent = history[-5:]  # 最近 5 次
        avg_score = sum(r.score for r in recent) / len(recent)

        # 趋势方向
        if len(recent) >= 3:
            scores = [r.score for r in recent]
            # 简单线性趋势
            n = len(scores)
            x_mean = (n - 1) / 2
            y_mean = sum(scores) / n
            numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            if denominator > 0:
                slope = numerator / denominator
                return slope

        return 0.0

    def _compute_score(
        self,
        performance_delta: float,
        side_effects: List[str],
        trend: float,
    ) -> float:
        """
        综合评分。

        score = performance_delta * 0.5 + trend * 0.3 - side_effects_penalty * 0.2
        """
        side_penalty = len(side_effects) * 0.1

        score = (
            performance_delta * 0.5 +
            trend * 0.3 -
            side_penalty * 0.2
        )

        return max(min(score, 1.0), -1.0)

    def _make_decision(
        self,
        score: float,
        mutation: Mutation,
        trend: float,
    ) -> AdoptionDecision:
        """根据评分做决策"""
        if score >= self.ACCEPT_THRESHOLD:
            return AdoptionDecision.ACCEPT
        elif score <= self.REJECT_THRESHOLD:
            return AdoptionDecision.REJECT
        elif trend < 0:
            # 趋势不好 → 建议回滚
            return AdoptionDecision.ROLLBACK
        else:
            return AdoptionDecision.TRIAL

    def _generate_reasoning(
        self,
        decision: AdoptionDecision,
        performance_delta: float,
        side_effects: List[str],
        trend: float,
    ) -> str:
        """生成推理说明"""
        parts = []

        if performance_delta > 0:
            parts.append(f"性能提升 {performance_delta:.2%}")
        elif performance_delta < 0:
            parts.append(f"性能下降 {abs(performance_delta):.2%}")
        else:
            parts.append("性能无明显变化")

        if side_effects:
            parts.append(f"检测到 {len(side_effects)} 个副作用: {'; '.join(side_effects)}")

        if trend > 0.05:
            parts.append("趋势向好")
        elif trend < -0.05:
            parts.append("趋势恶化")

        return " | ".join(parts)

    def _generate_recommendations(
        self,
        decision: AdoptionDecision,
        mutation: Mutation,
        performance_delta: float,
    ) -> List[str]:
        """生成建议"""
        recs = []

        if decision == AdoptionDecision.ACCEPT:
            recs.append("建议采纳此突变")
            recs.append(f"突变类型: {mutation.mutation_type.value}")
            if performance_delta > 0.2:
                recs.append("性能提升显著，考虑在更多 Agent 上应用")
        elif decision == AdoptionDecision.REJECT:
            recs.append("建议拒绝此突变")
            recs.append("性能未达标或产生负面效果")
        elif decision == AdoptionDecision.TRIAL:
            recs.append(f"建议继续观察（需至少 {self.TRIAL_PERIOD_TASKS} 个任务样本）")
        elif decision == AdoptionDecision.ROLLBACK:
            recs.append("趋势恶化，建议回滚到突变前状态")

        return recs
