"""
Evo - 固化引擎 (Solidify)

将提取出的基因 (Gene) 固化为可复用的记忆体 (Capsule)。

固化流程：
1. 验证基因质量（支持度、置信度）
2. 去重和合并相似基因
3. 生成记忆体模板
4. 持久化存储
5. 应用到匹配引擎

GEP 协议映射:
  SolidifiedPattern  →  Capsule
  weight_adjustments →  epigenetic_marks 里的 score 标记
  PatternStatus      →  outcome.score 范围映射
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from evo.gep_protocol import Capsule, EpigeneticMark
from evo.distillation.distiller import Gene, RuleType

logger = logging.getLogger(__name__)


class PatternStatus(str, Enum):
    """模式状态 — 映射到 Capsule.outcome.score 范围:
    DRAFT       → score < 0.6
    VALIDATED   → 0.6 <= score < 0.8
    SOLIDIFIED  → score >= 0.8
    DEPRECATED  → 已废弃
    """
    DRAFT = "draft"             # 草稿，未验证
    VALIDATED = "validated"     # 已验证，可试用
    SOLIDIFIED = "solidified"   # 已固化，正式使用
    DEPRECATED = "deprecated"   # 已废弃


def score_to_status(score: float) -> PatternStatus:
    """根据置信度/分数决定模式状态"""
    if score >= 0.8:
        return PatternStatus.SOLIDIFIED
    elif score >= 0.6:
        return PatternStatus.VALIDATED
    else:
        return PatternStatus.DRAFT


class Solidifier:
    """
    基因固化引擎（原 Solidifier，现输出 GEP Capsule）

    用法：
        solidifier = Solidifier()
        capsules = solidifier.solidify(genes)
    """

    # 固化阈值
    MIN_CONFIDENCE = 0.6
    MIN_SUPPORT = 3
    # 相似度阈值（用于去重）
    SIMILARITY_THRESHOLD = 0.8

    def __init__(self):
        self._capsules: Dict[str, Capsule] = {}
        self._pattern_counter = 0
        # 记录已处理的基因指纹
        self._rule_fingerprints: Set[str] = set()

    def solidify(self, genes: List[Gene]) -> List[Capsule]:
        """
        将基因固化为记忆体 (Capsule)。

        Args:
            genes: GEP 基因列表

        Returns:
            固化后的 Capsule 列表
        """
        new_capsules = []

        # 1. 过滤低质量基因
        qualified_genes = self._filter_qualified_genes(genes)

        # 2. 去重
        unique_genes = self._deduplicate_genes(qualified_genes)

        # 3. 合并相似基因
        merged_genes = self._merge_similar_genes(unique_genes)

        # 4. 生成记忆体
        for gene in merged_genes:
            capsule = self._create_capsule(gene)
            self._capsules[capsule.id] = capsule
            new_capsules.append(capsule)

        logger.info(
            "Solidified %d capsules from %d genes (%d qualified, %d unique, %d merged)",
            len(new_capsules), len(genes),
            len(qualified_genes), len(unique_genes), len(merged_genes),
        )
        return new_capsules

    def get_capsules(
        self,
        status: Optional[PatternStatus] = None,
        pattern_type: Optional[str] = None,
    ) -> List[Capsule]:
        """获取固化记忆体"""
        capsules = list(self._capsules.values())
        if status:
            capsules = [c for c in capsules if c._status == status.value]
        if pattern_type:
            capsules = [c for c in capsules if c._pattern_type == pattern_type]
        return capsules

    # 向后兼容别名
    def get_patterns(
        self,
        status: Optional[PatternStatus] = None,
        pattern_type: Optional[RuleType] = None,
    ) -> List[Capsule]:
        """向后兼容: 获取记忆体（原 get_patterns）"""
        pt = pattern_type.value if pattern_type else None
        return self.get_capsules(status, pt)

    def get_capsule(self, capsule_id: str) -> Optional[Capsule]:
        """按 ID 获取记忆体"""
        return self._capsules.get(capsule_id)

    # 向后兼容别名
    def get_pattern(self, pattern_id: str) -> Optional[Capsule]:
        """向后兼容: 按 ID 获取记忆体"""
        return self.get_capsule(pattern_id)

    def promote_capsule(self, capsule_id: str, new_status: PatternStatus) -> Optional[Capsule]:
        """提升记忆体状态"""
        capsule = self._capsules.get(capsule_id)
        if capsule:
            capsule._status = new_status.value
            capsule.updated_at = datetime.now()  # type: ignore
            logger.info("Capsule %s promoted to %s", capsule_id, new_status.value)
        return capsule

    # 向后兼容别名
    def promote_pattern(self, pattern_id: str, new_status: PatternStatus) -> Optional[Capsule]:
        """向后兼容: 提升记忆体状态"""
        return self.promote_capsule(pattern_id, new_status)

    def record_usage(self, capsule_id: str, success: bool) -> None:
        """记录记忆体使用情况"""
        capsule = self._capsules.get(capsule_id)
        if capsule:
            capsule._usage_count += 1
            # 更新成功率（移动平均）
            alpha = 0.1
            capsule._success_rate = capsule._success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha

    def deprecate_capsule(self, capsule_id: str, reason: str = "") -> Optional[Capsule]:
        """废弃记忆体"""
        capsule = self._capsules.get(capsule_id)
        if capsule:
            capsule._status = PatternStatus.DEPRECATED.value
            capsule._tags.append(f"deprecated:{reason}")
            logger.info("Capsule %s deprecated: %s", capsule_id, reason)
        return capsule

    # 向后兼容别名
    def deprecate_pattern(self, pattern_id: str, reason: str = "") -> Optional[Capsule]:
        """向后兼容: 废弃记忆体"""
        return self.deprecate_capsule(pattern_id, reason)

    # ---------- 内部方法 ----------

    def _filter_qualified_genes(self, genes: List[Gene]) -> List[Gene]:
        """过滤低质量基因"""
        qualified = []
        for g in genes:
            if g.confidence >= self.MIN_CONFIDENCE and g.support_count >= self.MIN_SUPPORT:
                qualified.append(g)
            elif g.category == "anti_pattern":
                # 反模式降低阈值
                if g.confidence >= 0.4 and g.support_count >= 1:
                    qualified.append(g)
        logger.info("Filtered %d/%d genes as qualified", len(qualified), len(genes))
        return qualified

    def _compute_fingerprint(self, gene: Gene) -> str:
        """计算基因指纹（用于去重）"""
        content = json.dumps({
            "conditions": gene.conditions,
            "action": gene.action,
            "category": gene.category,
        }, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()

    def _deduplicate_genes(self, genes: List[Gene]) -> List[Gene]:
        """去重基因"""
        unique = []
        for g in genes:
            fp = self._compute_fingerprint(g)
            if fp not in self._rule_fingerprints:
                self._rule_fingerprints.add(fp)
                unique.append(g)
        logger.info("Deduplicated: %d -> %d genes", len(genes), len(unique))
        return unique

    def _merge_similar_genes(self, genes: List[Gene]) -> List[Gene]:
        """合并相似基因"""
        if not genes:
            return genes

        merged = []
        used = set()

        for i, g1 in enumerate(genes):
            if i in used:
                continue

            similar = [g1]
            for j, g2 in enumerate(genes):
                if j <= i or j in used:
                    continue
                if self._genes_similar(g1, g2):
                    similar.append(g2)
                    used.add(j)

            if len(similar) > 1:
                # 合并
                merged_gene = self._merge_genes(similar)
                merged.append(merged_gene)
            else:
                merged.append(g1)
                used.add(i)

        return merged

    def _genes_similar(self, g1: Gene, g2: Gene) -> bool:
        """判断两个基因是否相似"""
        if g1.category != g2.category:
            return False

        # 比较条件
        c1_keys = set(g1.conditions.keys())
        c2_keys = set(g2.conditions.keys())
        overlap = len(c1_keys & c2_keys) / max(len(c1_keys | c2_keys), 1)

        return overlap >= self.SIMILARITY_THRESHOLD

    def _merge_genes(self, genes: List[Gene]) -> Gene:
        """合并多个相似基因"""
        base = genes[0]
        merged_conditions = dict(base.conditions)
        merged_source_ids = []

        for g in genes:
            merged_conditions.update(g.conditions)
            merged_source_ids.extend(g.source_task_ids)

        # 平均置信度
        avg_confidence = sum(g.confidence for g in genes) / len(genes)
        total_support = sum(g.support_count for g in genes)

        # 合并标签
        merged_tags = list(base.tags)
        for g in genes[1:]:
            merged_tags.extend(g.tags)
        merged_tags = list(set(merged_tags))
        merged_tags.append(f"merged:{len(genes)}")

        merged_marks = list(base.epigenetic_marks)
        for g in genes[1:]:
            merged_marks.extend(g.epigenetic_marks)

        merged = Gene(
            id=base.id,
            category=base.category,
            signals_match=base.signals_match,
            preconditions=base.preconditions,
            strategy=base.strategy,
            constraints=base.constraints,
            validation=base.validation,
            epigenetic_marks=merged_marks,
            asset_id=base.asset_id,
            _name=f"[合并] {base.name}",
            _description=f"合并 {len(genes)} 条相似基因: {base.description}",
            _support_count=total_support,
            _confidence=avg_confidence,
            _source_task_ids=list(set(merged_source_ids)),
            _tags=merged_tags,
            _conditions=merged_conditions,
            _action=base.action,
        )
        return merged

    def _create_capsule(self, gene: Gene) -> Capsule:
        """从基因创建固化记忆体 (Capsule)"""
        self._pattern_counter += 1

        # 根据基因类型生成权重调整（存为 epigenetic_marks）
        weight_adjustments: Dict[str, float] = {}
        epigenetic_marks: List[EpigeneticMark] = list(gene.epigenetic_marks)

        if gene.category == "capability":
            caps = gene.action.get("recommended_capabilities", [])
            for cap in caps:
                weight_adjustments[cap] = 0.1  # 推荐能力 +10% 权重
                epigenetic_marks.append(EpigeneticMark(
                    mark=f"weight:{cap}",
                    value=0.1,
                ))

        # 添加 score 标记
        epigenetic_marks.append(EpigeneticMark(
            mark="score",
            value=gene.confidence,
            timestamp=datetime.now().isoformat(),
        ))

        # 根据置信度决定初始状态
        status = score_to_status(gene.confidence)

        # 构建 outcome
        outcome = {
            "status": "success" if gene.confidence >= 0.6 else "pending",
            "score": gene.confidence,
        }

        # 构建 blast_radius
        blast_radius = {
            "source_genes": [gene.id],
            "category": gene.category,
        }

        # 构建 a2a
        a2a = {
            "source": "local",
            "ready_for_hub": gene.confidence >= 0.78,
            "quality_score": gene.confidence,
        }

        capsule = Capsule(
            id=f"capsule-{self._pattern_counter:04d}",
            trigger=gene.signals_match,
            gene=gene.id,
            summary=gene.description,
            confidence=gene.confidence,
            blast_radius=blast_radius,
            outcome=outcome,
            success_streak=1 if gene.confidence >= 0.6 else 0,
            content=gene.description,
            strategy=gene.strategy,
            a2a=a2a,
            # 兼容字段
            _pattern_id=f"pattern-{self._pattern_counter:04d}",
            _pattern_type=gene.category,
            _status=status.value,
            _match_conditions=gene.conditions,
            _template=gene.action,
            _weight_adjustments=weight_adjustments,
            _source_rule_ids=[gene.id],
            _tags=gene.tags,
        )
        return capsule
