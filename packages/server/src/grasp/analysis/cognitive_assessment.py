"""
认知评估服务 - 4 维度认知健康度评估

从 cognitions.jsonl 和 trace reports 计算：
1. Retrieval Quality (检索质量) - 检索出的认知质量和置信度
2. Context Utilization (上下文利用率) - 标签覆盖率和元数据完整度
3. Injection Accuracy (注入准确率) - 注入后直接发布的比例
4. Knowledge Freshness (知识新鲜度) - 认知的时效性

用法：
    from grasp.analysis.cognitive_assessment import CognitiveAssessmentService
    service = CognitiveAssessmentService()
    result = service.assess(agent_id="xxx")
"""

import json
import math
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field


# ==================== 数据路径 ====================

# cognitions.jsonl 的可能位置（按优先级排序）
COGNITIONS_PATHS = [
    Path(__file__).parent.parent.parent / "data" / "memory" / "grasp" / "cognitions.jsonl",
    Path(__file__).parent.parent.parent / "src" / "memory" / "grasp" / "cognitions.jsonl",
    Path(__file__).parent.parent.parent / "skills" / "grasp" / "memory" / "grasp" / "cognitions.jsonl",
]

# Trace reports 的可能位置
TRACE_REPORT_PATHS = [
    Path(__file__).parent.parent.parent / "data" / "memory" / "reins",
    Path(__file__).parent.parent.parent / "data" / "memory",
]


# ==================== 评估结果模型 ====================

@dataclass
class DimensionScore:
    """单个维度评分"""
    score: float  # 0-1
    label: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "label": self.label,
            "description": self.description,
            "details": self.details,
        }


@dataclass
class CognitiveAssessment:
    """认知评估结果"""
    agent_id: str
    overall_score: float
    dimensions: Dict[str, DimensionScore]
    stats: Dict[str, Any]
    assessed_at: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall_score": round(self.overall_score, 4),
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "stats": self.stats,
            "assessed_at": self.assessed_at,
            "recommendation": self.recommendation,
        }


# ==================== 数据加载 ====================

def load_cognitions(paths: List[Path] = None) -> List[Dict[str, Any]]:
    """从所有可用路径加载 cognitions"""
    search_paths = paths or COGNITIONS_PATHS
    all_cognitions = []
    seen_ids = set()

    for p in search_paths:
        if p.exists():
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            cid = record.get('cognition_id', '')
                            if cid and cid not in seen_ids:
                                seen_ids.add(cid)
                                all_cognitions.append(record)
                        except json.JSONDecodeError:
                            continue
            except (IOError, OSError):
                continue

    return all_cognitions


def load_trace_reports(paths: List[Path] = None) -> List[Dict[str, Any]]:
    """加载 trace reports（如果有）"""
    search_paths = paths or TRACE_REPORT_PATHS
    reports = []

    for p in search_paths:
        if p.exists():
            for f in p.iterdir():
                if f.suffix == '.jsonl' and 'trace' in f.name.lower():
                    try:
                        with open(f, 'r', encoding='utf-8') as fh:
                            for line in fh:
                                line = line.strip()
                                if line:
                                    try:
                                        reports.append(json.loads(line))
                                    except json.JSONDecodeError:
                                        continue
                    except (IOError, OSError):
                        continue

    return reports


# ==================== 4 维度评估 ====================

def calc_retrieval_quality(cognitions: List[Dict], agent_id: str) -> DimensionScore:
    """
    检索质量 (Retrieval Quality)

    衡量该 Agent 相关的认知检索质量：
    - 平均 quality_score
    - 平均 confidence
    - 高质量认知比例 (quality_score >= 0.8)
    """
    agent_cogs = [c for c in cognitions if c.get('source', {}).get('agent_id') == agent_id]

    if not agent_cogs:
        # 如果该 agent 没有直接认知，使用全部数据作为参考
        agent_cogs = cognitions

    if not agent_cogs:
        return DimensionScore(
            score=0.0,
            label="无数据",
            description="无可用的认知数据",
            details={"count": 0},
        )

    quality_scores = [c.get('quality_score', 0) for c in agent_cogs]
    confidences = [c.get('confidence', 0) for c in agent_cogs]

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    high_quality_count = sum(1 for qs in quality_scores if qs >= 0.8)
    high_quality_ratio = high_quality_count / len(agent_cogs) if agent_cogs else 0

    # 综合评分：quality(40%) + confidence(30%) + high_quality_ratio(30%)
    score = avg_quality * 0.4 + avg_confidence * 0.3 + high_quality_ratio * 0.3

    # 评级
    if score >= 0.8:
        label = "优秀"
    elif score >= 0.6:
        label = "良好"
    elif score >= 0.4:
        label = "一般"
    else:
        label = "待改进"

    return DimensionScore(
        score=score,
        label=label,
        description=f"检索质量评估：基于 {len(agent_cogs)} 条认知的质量和置信度",
        details={
            "total_cognitions": len(agent_cogs),
            "avg_quality_score": round(avg_quality, 4),
            "avg_confidence": round(avg_confidence, 4),
            "high_quality_ratio": round(high_quality_ratio, 4),
            "quality_distribution": {
                "excellent": sum(1 for qs in quality_scores if qs >= 0.9),
                "good": sum(1 for qs in quality_scores if 0.7 <= qs < 0.9),
                "fair": sum(1 for qs in quality_scores if 0.4 <= qs < 0.7),
                "poor": sum(1 for qs in quality_scores if qs < 0.4),
            },
        },
    )


def calc_context_utilization(cognitions: List[Dict], agent_id: str) -> DimensionScore:
    """
    上下文利用率 (Context Utilization)

    衡量认知的元数据完整度和标签覆盖率：
    - 平均标签数
    - 有元数据的比例
    - 标签多样性（唯一标签数）
    """
    agent_cogs = [c for c in cognitions if c.get('source', {}).get('agent_id') == agent_id]
    if not agent_cogs:
        agent_cogs = cognitions

    if not agent_cogs:
        return DimensionScore(
            score=0.0,
            label="无数据",
            description="无可用的认知数据",
            details={"count": 0},
        )

    tag_counts = [len(c.get('tags', [])) for c in agent_cogs]
    avg_tags = sum(tag_counts) / len(agent_cogs) if tag_counts else 0

    # 有 metadata 的比例
    has_metadata = sum(1 for c in agent_cogs if c.get('metadata'))
    metadata_ratio = has_metadata / len(agent_cogs) if agent_cogs else 0

    # 标签多样性
    all_tags = set()
    for c in agent_cogs:
        all_tags.update(c.get('tags', []))
    tag_diversity = len(all_tags)
    unique_tag_ratio = min(tag_diversity / max(len(agent_cogs), 1), 1.0)

    # 综合评分：avg_tags_norm(30%) + metadata_ratio(35%) + unique_tag_ratio(35%)
    # 归一化平均标签数（假设 3 个标签为满分）
    avg_tags_norm = min(avg_tags / 3.0, 1.0)

    score = avg_tags_norm * 0.3 + metadata_ratio * 0.35 + unique_tag_ratio * 0.35

    if score >= 0.8:
        label = "优秀"
    elif score >= 0.6:
        label = "良好"
    elif score >= 0.4:
        label = "一般"
    else:
        label = "待改进"

    # 类型分布
    type_counts = {}
    for c in agent_cogs:
        t = c.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    return DimensionScore(
        score=score,
        label=label,
        description=f"上下文利用率评估：标签多样性和元数据完整度",
        details={
            "total_cognitions": len(agent_cogs),
            "avg_tags_per_cognition": round(avg_tags, 2),
            "metadata_coverage": round(metadata_ratio, 4),
            "unique_tags": tag_diversity,
            "unique_tag_ratio": round(unique_tag_ratio, 4),
            "type_distribution": type_counts,
            "top_tags": sorted(
                [(t, sum(1 for c in agent_cogs if t in c.get('tags', [])))
                 for t in all_tags],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        },
    )


def calc_injection_accuracy(cognitions: List[Dict], agent_id: str) -> DimensionScore:
    """
    注入准确率 (Injection Accuracy)

    衡量认知注入的准确性和质量：
    - 直接发布比例（published vs pending_review）
    - 高置信度注入比例（confidence >= 0.8）
    - 无拒绝记录
    """
    agent_cogs = [c for c in cognitions if c.get('source', {}).get('agent_id') == agent_id]
    if not agent_cogs:
        agent_cogs = cognitions

    if not agent_cogs:
        return DimensionScore(
            score=0.0,
            label="无数据",
            description="无可用的认知数据",
            details={"count": 0},
        )

    status_counts = {}
    for c in agent_cogs:
        s = c.get('status', 'unknown')
        status_counts[s] = status_counts.get(s, 0) + 1

    total = len(agent_cogs)
    published = status_counts.get('published', 0)
    pending = status_counts.get('pending_review', 0)
    rejected = status_counts.get('rejected', 0)

    publish_ratio = published / total if total else 0
    # pending_review 算半成功（需要审核但非拒绝）
    effective_ratio = (published + pending * 0.5) / total if total else 0

    # 高置信度注入比例
    high_conf_count = sum(1 for c in agent_cogs if c.get('confidence', 0) >= 0.8)
    high_conf_ratio = high_conf_count / total if total else 0

    # 无拒绝奖励
    no_rejection_bonus = 0.1 if rejected == 0 else 0
    rejection_penalty = min(rejected / max(total, 1), 0.3)

    # 综合评分：effective_ratio(40%) + high_conf_ratio(40%) + rejection_adjustment(20%)
    rejection_adj = max(0, 1 - rejection_penalty * 3)  # 每 33% 拒绝率扣 100%
    score = effective_ratio * 0.4 + high_conf_ratio * 0.4 + rejection_adj * 0.2
    score = min(score + no_rejection_bonus, 1.0)

    if score >= 0.8:
        label = "优秀"
    elif score >= 0.6:
        label = "良好"
    elif score >= 0.4:
        label = "一般"
    else:
        label = "待改进"

    return DimensionScore(
        score=score,
        label=label,
        description=f"注入准确率评估：发布状态和置信度分布",
        details={
            "total_cognitions": total,
            "status_distribution": status_counts,
            "publish_ratio": round(publish_ratio, 4),
            "effective_ratio": round(effective_ratio, 4),
            "high_confidence_ratio": round(high_conf_ratio, 4),
            "rejected_count": rejected,
            "rejection_rate": round(rejected / total if total else 0, 4),
        },
    )


def calc_knowledge_freshness(cognitions: List[Dict], agent_id: str) -> DimensionScore:
    """
    知识新鲜度 (Knowledge Freshness)

    衡量认知知识库的时效性：
    - 最近 7 天新增比例
    - 最近 30 天新增比例
    - 平均知识年龄
    - 最老/最新知识时间跨度
    """
    agent_cogs = [c for c in cognitions if c.get('source', {}).get('agent_id') == agent_id]
    if not agent_cogs:
        agent_cogs = cognitions

    if not agent_cogs:
        return DimensionScore(
            score=0.0,
            label="无数据",
            description="无可用的认知数据",
            details={"count": 0},
        )

    now = datetime.now(timezone.utc)
    ages_days = []

    for c in agent_cogs:
        created = c.get('created_at', '')
        if created:
            try:
                # 解析 ISO 8601 格式
                if created.endswith('Z'):
                    created = created[:-1] + '+00:00'
                dt = datetime.fromisoformat(created)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age = (now - dt).total_seconds() / 86400
                ages_days.append(max(age, 0))
            except (ValueError, TypeError):
                pass

    if not ages_days:
        return DimensionScore(
            score=0.0,
            label="无有效时间戳",
            description="认知数据中无有效时间戳",
            details={"count": len(agent_cogs)},
        )

    total = len(ages_days)
    recent_7d = sum(1 for a in ages_days if a <= 7)
    recent_30d = sum(1 for a in ages_days if a <= 30)
    recent_90d = sum(1 for a in ages_days if a <= 90)

    ratio_7d = recent_7d / total
    ratio_30d = recent_30d / total
    ratio_90d = recent_90d / total

    avg_age = sum(ages_days) / total
    max_age = max(ages_days)
    min_age = min(ages_days)

    # 综合评分：7d_ratio(30%) + 30d_ratio(30%) + age_freshness(40%)
    # 年龄新鲜度：平均年龄越短越好，30天内为满分
    age_freshness = max(0, 1 - avg_age / 90)  # 90天平均年龄 = 0分

    score = ratio_7d * 0.3 + ratio_30d * 0.3 + age_freshness * 0.4

    if score >= 0.8:
        label = "优秀"
    elif score >= 0.6:
        label = "良好"
    elif score >= 0.4:
        label = "一般"
    else:
        label = "待改进"

    return DimensionScore(
        score=score,
        label=label,
        description=f"知识新鲜度评估：基于认知创建时间的时效性分析",
        details={
            "total_cognitions": total,
            "recent_7d": recent_7d,
            "recent_7d_ratio": round(ratio_7d, 4),
            "recent_30d": recent_30d,
            "recent_30d_ratio": round(ratio_30d, 4),
            "recent_90d": recent_90d,
            "recent_90d_ratio": round(ratio_90d, 4),
            "avg_age_days": round(avg_age, 1),
            "max_age_days": round(max_age, 1),
            "min_age_days": round(min_age, 1),
        },
    )


def generate_recommendation(dimensions: Dict[str, DimensionScore]) -> str:
    """根据各维度评分生成建议"""
    scores = {k: v.score for k, v in dimensions.items()}
    weakest = min(scores, key=scores.get)
    weakest_score = scores[weakest]

    recommendations = {
        "retrieval_quality": "建议提高认知质量标准和置信度阈值，增加高质量认知比例",
        "context_utilization": "建议为认知添加更多标签和元数据，提升上下文覆盖度",
        "injection_accuracy": "建议优化注入流程，减少待审核和拒绝的认知数量",
        "knowledge_freshness": "建议定期更新认知知识库，注入最新认知以保持时效性",
    }

    label_map = {
        "retrieval_quality": "检索质量",
        "context_utilization": "上下文利用率",
        "injection_accuracy": "注入准确率",
        "knowledge_freshness": "知识新鲜度",
    }

    if weakest_score >= 0.8:
        return "所有维度表现优秀，继续保持当前认知管理策略"
    elif weakest_score >= 0.6:
        return f"整体表现良好，{label_map.get(weakest, weakest)}维度有提升空间：{recommendations.get(weakest, '')}"
    elif weakest_score >= 0.4:
        return f"需要关注 {label_map.get(weakest, weakest)} 维度：{recommendations.get(weakest, '')}"
    else:
        return f"建议优先改进 {label_map.get(weakest, weakest)} 维度：{recommendations.get(weakest, '')}"


# ==================== 主服务类 ====================

class CognitiveAssessmentService:
    """认知评估服务 - 4 维度评估"""

    def assess(self, agent_id: str, all_cognitions: List[Dict] = None) -> CognitiveAssessment:
        """
        执行 4 维度认知评估

        :param agent_id: Agent ID
        :param all_cognitions: 可选，预加载的认知数据（用于测试）
        :return: CognitiveAssessment 评估结果
        """
        cognitions = all_cognitions or load_cognitions()

        dimensions = {
            "retrieval_quality": calc_retrieval_quality(cognitions, agent_id),
            "context_utilization": calc_context_utilization(cognitions, agent_id),
            "injection_accuracy": calc_injection_accuracy(cognitions, agent_id),
            "knowledge_freshness": calc_knowledge_freshness(cognitions, agent_id),
        }

        # 综合评分：4 维度等权重
        dim_scores = [d.score for d in dimensions.values()]
        overall = sum(dim_scores) / len(dim_scores) if dim_scores else 0

        # 统计信息
        agent_cogs = [c for c in cognitions if c.get('source', {}).get('agent_id') == agent_id]
        type_dist = {}
        for c in (agent_cogs or cognitions):
            t = c.get('type', 'unknown')
            type_dist[t] = type_dist.get(t, 0) + 1

        stats = {
            "total_cognitions": len(agent_cogs) if agent_cogs else len(cognitions),
            "total_loaded": len(cognitions),
            "type_distribution": type_dist,
            "data_sources": [str(p) for p in COGNITIONS_PATHS if p.exists()],
        }

        recommendation = generate_recommendation(dimensions)

        return CognitiveAssessment(
            agent_id=agent_id,
            overall_score=overall,
            dimensions=dimensions,
            stats=stats,
            assessed_at=datetime.now(timezone.utc).isoformat(),
            recommendation=recommendation,
        )


# 全局实例
_default_service: Optional[CognitiveAssessmentService] = None


def get_assessment_service() -> CognitiveAssessmentService:
    global _default_service
    if _default_service is None:
        _default_service = CognitiveAssessmentService()
    return _default_service
