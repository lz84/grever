"""
Vigil - 信任系统 (Trust)

基于 Agent 历史执行记录计算信任分数。

信任分数模型：
  trust_score = (success_rate * 0.4 + consistency * 0.2 + timeliness * 0.2 + quality * 0.2) * reputation_multiplier

评分范围: 0.0 ~ 1.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    """信任等级"""
    UNTRUSTED = "untrusted"      # < 0.2
    LOW = "low"                   # 0.2 ~ 0.4
    MODERATE = "moderate"         # 0.4 ~ 0.6
    TRUSTED = "trusted"           # 0.6 ~ 0.8
    HIGHLY_TRUSTED = "high"       # >= 0.8


@dataclass
class TrustMetrics:
    """Agent 信任度指标"""
    agent_id: str
    total_tasks: int = 0
    success_count: int = 0
    failed_count: int = 0
    timeout_count: int = 0
    avg_response_time_ms: float = 0.0
    avg_quality_score: float = 0.0  # 0~1，由 verifier 或人工评估
    consecutive_failures: int = 0
    last_evaluated_at: Optional[datetime] = None
    # 时间衰减权重：最近的任务影响更大
    recent_tasks_weight: float = 1.0  # 最近 7 天
    older_tasks_weight: float = 0.5   # 7~30 天
    stale_tasks_weight: float = 0.2   # 30+ 天


@dataclass
class TrustScore:
    """信任评分结果"""
    agent_id: str
    score: float  # 0.0 ~ 1.0
    level: TrustLevel
    confidence: float  # 0.0 ~ 1.0, 基于样本量
    metrics: TrustMetrics
    breakdown: Dict[str, float]  # 各维度得分
    evaluated_at: datetime = field(default_factory=datetime.now)


class TrustEvaluator:
    """
    Agent 信任度评估器

    用法：
        evaluator = TrustEvaluator()
        score = evaluator.evaluate(agent_id, history_records)
    """

    # 权重配置
    WEIGHT_SUCCESS_RATE = 0.35
    WEIGHT_CONSISTENCY = 0.20
    WEIGHT_TIMELINESS = 0.20
    WEIGHT_QUALITY = 0.15
    WEIGHT_LONGEVITY = 0.10

    # 信任等级阈值
    THRESHOLD_UNTRUSTED = 0.2
    THRESHOLD_LOW = 0.4
    THRESHOLD_MODERATE = 0.6
    THRESHOLD_TRUSTED = 0.8

    # 连续失败惩罚
    CONSECUTIVE_FAILURE_PENALTY = 0.05  # 每次连续失败扣 5%

    # 时间衰减配置（天）
    RECENT_DAYS = 7
    OLDER_DAYS = 30

    # 置信度配置
    MIN_SAMPLES_FOR_CONFIDENCE = 5
    FULL_CONFIDENCE_SAMPLES = 50

    def __init__(self, config: Optional[Dict] = None):
        if config:
            self.WEIGHT_SUCCESS_RATE = config.get("weight_success_rate", self.WEIGHT_SUCCESS_RATE)
            self.WEIGHT_CONSISTENCY = config.get("weight_consistency", self.WEIGHT_CONSISTENCY)
            self.WEIGHT_TIMELINESS = config.get("weight_timeliness", self.WEIGHT_TIMELINESS)
            self.WEIGHT_QUALITY = config.get("weight_quality", self.WEIGHT_QUALITY)
            self.WEIGHT_LONGEVITY = config.get("weight_longevity", self.WEIGHT_LONGEVITY)

        # 内存缓存: agent_id -> TrustScore
        self._cache: Dict[str, TrustScore] = {}

    def evaluate(
        self,
        agent_id: str,
        history_records: List[Dict],
        now: Optional[datetime] = None,
    ) -> TrustScore:
        """
        评估 Agent 信任度。

        Args:
            agent_id: Agent ID
            history_records: 历史执行记录列表，每条包含：
                - status: "success" | "failed" | "timeout"
                - quality_score: 0.0~1.0 (可选)
                - duration_ms: 执行时长 (可选)
                - created_at: 记录时间
                - task_type: 任务类型 (可选)
            now: 当前时间（用于时间衰减计算）

        Returns:
            TrustScore 评分结果
        """
        now = now or datetime.now()
        metrics = self._compute_metrics(agent_id, history_records, now)
        breakdown = self._compute_breakdown(metrics, history_records, now)
        score = self._aggregate_score(breakdown, metrics)
        level = self._classify_level(score)
        confidence = self._compute_confidence(metrics.total_tasks)

        trust_score = TrustScore(
            agent_id=agent_id,
            score=round(score, 4),
            level=level,
            confidence=round(confidence, 4),
            metrics=metrics,
            breakdown={k: round(v, 4) for k, v in breakdown.items()},
        )

        self._cache[agent_id] = trust_score
        logger.info(
            "Trust evaluation for %s: score=%.4f level=%s confidence=%.4f",
            agent_id, score, level, confidence,
        )
        return trust_score

    def get_cached(self, agent_id: str) -> Optional[TrustScore]:
        """获取缓存的信任评分"""
        return self._cache.get(agent_id)

    def clear_cache(self, agent_id: Optional[str] = None):
        """清除缓存"""
        if agent_id:
            self._cache.pop(agent_id, None)
        else:
            self._cache.clear()

    def _compute_metrics(
        self,
        agent_id: str,
        records: List[Dict],
        now: datetime,
    ) -> TrustMetrics:
        """从历史记录计算基础指标"""
        metrics = TrustMetrics(agent_id=agent_id)

        if not records:
            return metrics

        total_quality = 0.0
        quality_count = 0
        total_duration = 0.0
        duration_count = 0
        recent_cutoff = now - timedelta(days=self.RECENT_DAYS)
        older_cutoff = now - timedelta(days=self.OLDER_DAYS)

        sorted_records = sorted(
            records,
            key=lambda r: r.get("created_at", now),
            reverse=True,
        )

        for r in sorted_records:
            metrics.total_tasks += 1
            status = r.get("status", "").lower()

            if status == "success":
                metrics.success_count += 1
                metrics.consecutive_failures = 0
            elif status == "failed":
                metrics.failed_count += 1
                metrics.consecutive_failures += 1
            elif status == "timeout":
                metrics.timeout_count += 1
                metrics.consecutive_failures += 1

            if "quality_score" in r and r["quality_score"] is not None:
                total_quality += float(r["quality_score"])
                quality_count += 1

            if "duration_ms" in r and r["duration_ms"] is not None:
                total_duration += float(r["duration_ms"])
                duration_count += 1

        if quality_count > 0:
            metrics.avg_quality_score = total_quality / quality_count
        if duration_count > 0:
            metrics.avg_response_time_ms = total_duration / duration_count

        metrics.last_evaluated_at = now
        return metrics

    def _compute_breakdown(
        self,
        metrics: TrustMetrics,
        records: List[Dict],
        now: datetime,
    ) -> Dict[str, float]:
        """计算各维度得分 (0~1)"""
        # 1. 成功率 (加时间衰减)
        if metrics.total_tasks == 0:
            success_rate = 0.5  # 无数据默认中立
        else:
            weighted_success = 0.0
            weighted_total = 0.0
            for r in records:
                created = r.get("created_at", now)
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                age = (now - created).total_seconds() / 86400.0
                if age <= self.RECENT_DAYS:
                    w = self.recent_weight()
                elif age <= self.OLDER_DAYS:
                    w = self.older_weight()
                else:
                    w = self.stale_weight()

                weighted_total += w
                if r.get("status", "").lower() == "success":
                    weighted_success += w

            success_rate = weighted_success / max(weighted_total, 1)

        # 2. 一致性 (失败率的标准差)
        consistency = self._compute_consistency(records, now)

        # 3. 及时性
        timeliness = self._compute_timeliness(metrics)

        # 4. 质量
        quality = metrics.avg_quality_score if metrics.avg_quality_score > 0 else 0.5

        # 5. 持久性 (基于任务数量和跨度)
        longevity = self._compute_longevity(metrics, records, now)

        return {
            "success_rate": success_rate,
            "consistency": consistency,
            "timeliness": timeliness,
            "quality": quality,
            "longevity": longevity,
        }

    def _aggregate_score(self, breakdown: Dict[str, float], metrics: TrustMetrics) -> float:
        """聚合各维度得分为总分"""
        score = (
            breakdown["success_rate"] * self.WEIGHT_SUCCESS_RATE +
            breakdown["consistency"] * self.WEIGHT_CONSISTENCY +
            breakdown["timeliness"] * self.WEIGHT_TIMELINESS +
            breakdown["quality"] * self.WEIGHT_QUALITY +
            breakdown["longevity"] * self.WEIGHT_LONGEVITY
        )

        # 连续失败惩罚
        if metrics.consecutive_failures > 0:
            penalty = min(
                metrics.consecutive_failures * self.CONSECUTIVE_FAILURE_PENALTY,
                0.3  # 最多扣 30%
            )
            score = max(score - penalty, 0.0)

        return max(min(score, 1.0), 0.0)

    def _classify_level(self, score: float) -> TrustLevel:
        """将分数映射到信任等级"""
        if score >= self.THRESHOLD_TRUSTED:
            return TrustLevel.HIGHLY_TRUSTED
        elif score >= self.THRESHOLD_MODERATE:
            return TrustLevel.TRUSTED
        elif score >= self.THRESHOLD_LOW:
            return TrustLevel.MODERATE
        elif score >= self.THRESHOLD_UNTRUSTED:
            return TrustLevel.LOW
        else:
            return TrustLevel.UNTRUSTED

    def _compute_confidence(self, total_tasks: int) -> float:
        """基于样本量计算置信度"""
        if total_tasks < self.MIN_SAMPLES_FOR_CONFIDENCE:
            return total_tasks / max(self.MIN_SAMPLES_FOR_CONFIDENCE, 1) * 0.5
        elif total_tasks >= self.FULL_CONFIDENCE_SAMPLES:
            return 1.0
        else:
            ratio = (total_tasks - self.MIN_SAMPLES_FOR_CONFIDENCE) / \
                    (self.FULL_CONFIDENCE_SAMPLES - self.MIN_SAMPLES_FOR_CONFIDENCE)
            return 0.5 + ratio * 0.5

    @staticmethod
    def _compute_consistency(records: List[Dict], now: datetime) -> float:
        """
        计算一致性得分 (0~1)

        基于最近 N 个任务的成功/失败交替频率。
        越稳定（连续成功或连续失败）一致性越高。
        """
        if len(records) < 2:
            return 0.5

        recent = records[-20:]  # 看最近 20 条
        transitions = 0
        for i in range(1, len(recent)):
            prev_ok = recent[i - 1].get("status", "").lower() == "success"
            curr_ok = recent[i].get("status", "").lower() == "success"
            if prev_ok != curr_ok:
                transitions += 1

        max_transitions = len(recent) - 1
        consistency = 1.0 - (transitions / max(max_transitions, 1))
        return round(consistency, 4)

    @staticmethod
    def _compute_timeliness(metrics: TrustMetrics) -> float:
        """
        计算及时性得分 (0~1)

        基于平均响应时间。假设：
        - < 1000ms: 满分
        - > 30000ms: 0 分
        - 中间线性插值
        """
        if metrics.avg_response_time_ms <= 0:
            return 0.5  # 无数据默认中立

        avg_ms = metrics.avg_response_time_ms
        if avg_ms <= 1000:
            return 1.0
        elif avg_ms >= 30000:
            return 0.0
        else:
            return round(1.0 - (avg_ms - 1000) / 29000, 4)

    @staticmethod
    def _compute_longevity(
        metrics: TrustMetrics,
        records: List[Dict],
        now: datetime,
    ) -> float:
        """
        计算持久性得分 (0~1)

        基于任务数量和活跃天数。
        """
        if metrics.total_tasks == 0:
            return 0.0

        # 任务数量分数 (log 尺度)
        import math
        task_score = min(math.log10(max(metrics.total_tasks, 1)) / 3, 1.0)

        # 活跃天数分数
        if records:
            timestamps = []
            for r in records:
                ts = r.get("created_at", now)
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                timestamps.append(ts)
            span_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400.0
            span_score = min(span_days / 90, 1.0)  # 90 天满分
        else:
            span_score = 0.0

        return round(task_score * 0.6 + span_score * 0.4, 4)

    @staticmethod
    def recent_weight() -> float:
        return 1.0

    @staticmethod
    def older_weight() -> float:
        return 0.5

    @staticmethod
    def stale_weight() -> float:
        return 0.2
