"""
Evo - 规则提取器 (Distiller)

从成功/失败任务中提取可复用的基因 (Gene)。

提取流程：
1. 收集任务执行记录
2. 分析成功/失败模式
3. 提取条件-动作基因
4. 计算基因置信度
5. 输出 GEP 协议格式的 Gene 列表

GEP 协议映射:
  ExtractedRule  →  Gene
  RuleType.*     →  Gene.category
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from evo.gep_protocol import EpigeneticMark, Gene

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """规则类型 → 映射到 Gene.category"""
    CAPABILITY = "capability"       # 能力规则：什么 Agent 适合什么任务
    PATTERN = "pattern"             # 模式规则：任务执行的通用模式
    ANTI_PATTERN = "anti_pattern"   # 反模式：应该避免的做法
    SEQUENCE = "sequence"           # 序列规则：任务执行顺序
    CONDITION = "condition"         # 条件规则：执行前提条件
    CONSTRAINT = "constraint"       # 约束规则：执行限制


class RuleDistiller:
    """
    基因提取器（原 RuleDistiller，现输出 GEP Gene）

    用法：
        distiller = RuleDistiller()
        genes = distiller.distill(task_records)
    """

    def __init__(self, min_support: int = 2, min_confidence: float = 0.5):
        self._min_support = min_support
        self._min_confidence = min_confidence
        self._genes: Dict[str, Gene] = {}
        self._rule_counter = 0

    def distill(self, task_records: List[Dict]) -> List[Gene]:
        """
        从任务记录中提取基因 (Gene)。

        Args:
            task_records: 任务执行记录列表，每条包含：
                - task_id: 任务 ID
                - task_type: 任务类型
                - task_category: 任务分类
                - required_capabilities: 所需能力
                - assigned_agent: 分配的 Agent ID
                - agent_capabilities: Agent 能力
                - status: 执行状态 (success/failed/timeout)
                - quality_score: 质量分数 (0~1)
                - duration_ms: 执行时长
                - error_type: 错误类型 (可选)
                - tags: 任务标签

        Returns:
            GEP Gene 列表
        """
        new_genes = []

        # 1. 提取能力匹配基因
        new_genes.extend(self._extract_capability_genes(task_records))

        # 2. 提取执行模式基因
        new_genes.extend(self._extract_pattern_genes(task_records))

        # 3. 提取反模式基因
        new_genes.extend(self._extract_anti_pattern_genes(task_records))

        # 4. 提取序列基因
        new_genes.extend(self._extract_sequence_genes(task_records))

        # 存储
        for gene in new_genes:
            self._genes[gene.id] = gene

        logger.info(
            "Distilled %d genes from %d task records",
            len(new_genes), len(task_records),
        )
        return new_genes

    def get_genes(self, category: Optional[str] = None) -> List[Gene]:
        """获取已提取的基因"""
        genes = list(self._genes.values())
        if category:
            genes = [g for g in genes if g.category == category]
        return genes

    def get_gene(self, gene_id: str) -> Optional[Gene]:
        """按 ID 获取基因"""
        return self._genes.get(gene_id)

    # 向后兼容别名
    def get_rules(self, rule_type: Optional[RuleType] = None) -> List[Gene]:
        """向后兼容: 获取基因（原 get_rules）"""
        category = rule_type.value if rule_type else None
        return self.get_genes(category)

    def get_rule(self, rule_id: str) -> Optional[Gene]:
        """向后兼容: 按 ID 获取基因"""
        return self.get_gene(rule_id)

    def update_gene_support(self, gene_id: str, supported: bool) -> None:
        """更新基因支持计数"""
        gene = self._genes.get(gene_id)
        if gene:
            if supported:
                gene._support_count += 1
            # 重新计算置信度
            total = gene._support_count + max(1, len(gene._source_task_ids) - gene._support_count)
            gene._confidence = gene._support_count / total if total > 0 else 0

    # 向后兼容别名
    def update_rule_support(self, rule_id: str, supported: bool) -> None:
        """向后兼容: 更新基因支持度"""
        self.update_gene_support(rule_id, supported)

    # ---------- 内部提取方法 ----------

    def _extract_capability_genes(self, records: List[Dict]) -> List[Gene]:
        """提取能力匹配基因：哪些能力组合适合哪些任务类型"""
        genes = []
        # 按任务类型+状态分组
        groups: Dict[str, List[Dict]] = {}
        for r in records:
            key = f"{r.get('task_type', 'unknown')}_{r.get('status', 'unknown')}"
            groups.setdefault(key, []).append(r)

        for key, group in groups.items():
            if len(group) < self._min_support:
                continue

            task_type = group[0].get("task_type", "unknown")
            status = group[0].get("status", "unknown")
            success = status == "success"

            # 统计成功/失败案例中的能力
            if success:
                capability_freq: Dict[str, int] = {}
                for r in group:
                    caps = r.get("agent_capabilities", {})
                    if isinstance(caps, dict):
                        for dim, tags in caps.items():
                            if isinstance(tags, list):
                                for tag in tags:
                                    capability_freq[tag] = capability_freq.get(tag, 0) + 1

                # 提取高频能力
                threshold = max(len(group) * 0.5, 1)
                high_freq_caps = [c for c, n in capability_freq.items() if n >= threshold]

                if high_freq_caps:
                    gene = self._create_gene(
                        category="capability",
                        name=f"能力匹配: {task_type}",
                        description=f"执行 {task_type} 任务的成功 Agent 通常具备能力: {high_freq_caps}",
                        conditions={"task_type": task_type},
                        action={"recommended_capabilities": high_freq_caps},
                        strategy=[{"action": "use_capabilities", "value": high_freq_caps}],
                        signals_match=[f"task:{task_type}"],
                        support_count=len(group),
                        confidence=len(group) / max(len(records), 1),
                        source_task_ids=[r.get("task_id", "") for r in group],
                        tags=[task_type, "capability"],
                    )
                    genes.append(gene)

        return genes

    def _extract_pattern_genes(self, records: List[Dict]) -> List[Gene]:
        """提取成功执行的模式基因"""
        genes = []
        success_records = [r for r in records if r.get("status") == "success"]

        if not success_records:
            return genes

        # 分析成功任务的共同特征
        # 1. 质量分数分布
        quality_scores = [r.get("quality_score", 0) for r in success_records if r.get("quality_score") is not None]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality > 0.7:
                gene = self._create_gene(
                    category="pattern",
                    name=f"高质量模式 (avg={avg_quality:.2f})",
                    description=f"任务平均质量分数 {avg_quality:.2f}，表明执行模式有效",
                    conditions={"min_quality": 0.7},
                    action={"pattern": "high_quality_execution"},
                    preconditions=["task_status==success", f"quality_score>={avg_quality:.2f}"],
                    strategy=[{"action": "follow_high_quality_pattern", "value": True}],
                    signals_match=["high_quality"],
                    support_count=len(success_records),
                    confidence=avg_quality,
                    source_task_ids=[r.get("task_id", "") for r in success_records],
                    tags=["quality", "pattern"],
                )
                genes.append(gene)

        # 2. 执行时长模式
        durations = [r.get("duration_ms", 0) for r in success_records if r.get("duration_ms")]
        if durations:
            avg_duration = sum(durations) / len(durations)
            gene = self._create_gene(
                category="pattern",
                name="执行时长基准",
                description=f"成功任务的平均执行时长: {avg_duration:.0f}ms",
                conditions={"task_status": "success"},
                action={"expected_duration_ms": round(avg_duration)},
                preconditions=["task_status==success"],
                strategy=[{"action": "expect_duration_ms", "value": round(avg_duration)}],
                signals_match=["duration_benchmark"],
                support_count=len(success_records),
                confidence=0.6 if len(durations) > 10 else 0.3,
                source_task_ids=[r.get("task_id", "") for r in success_records],
                tags=["duration", "benchmark"],
            )
            genes.append(gene)

        return genes

    def _extract_anti_pattern_genes(self, records: List[Dict]) -> List[Gene]:
        """提取反模式基因：应该避免的做法"""
        genes = []
        failed_records = [r for r in records if r.get("status") in ("failed", "timeout")]

        if not failed_records:
            return genes

        # 分析失败的共同原因
        error_types: Dict[str, List[Dict]] = {}
        for r in failed_records:
            et = r.get("error_type", "unknown")
            error_types.setdefault(et, []).append(r)

        for error_type, group in error_types.items():
            if len(group) < self._min_support:
                continue

            gene = self._create_gene(
                category="anti_pattern",
                name=f"反模式: {error_type}",
                description=f"错误类型 '{error_type}' 出现 {len(group)} 次，需要避免",
                conditions={"error_type": error_type},
                action={"avoid": True, "suggestion": f"检查并避免导致 {error_type} 的操作"},
                constraints={"forbidden_error_types": [error_type]},
                signals_match=[f"error:{error_type}"],
                support_count=len(group),
                confidence=min(len(group) / max(len(failed_records), 1), 1.0),
                source_task_ids=[r.get("task_id", "") for r in group],
                tags=[error_type, "anti_pattern"],
            )
            genes.append(gene)

        return genes

    def _extract_sequence_genes(self, records: List[Dict]) -> List[Gene]:
        """提取任务序列基因：哪些任务类型倾向于按特定顺序执行"""
        genes = []
        # 按 project_id 分组
        projects: Dict[str, List[Dict]] = {}
        for r in records:
            pid = r.get("project_id")
            if pid:
                projects.setdefault(pid, []).append(r)

        for pid, tasks in projects.items():
            if len(tasks) < 2:
                continue

            # 按完成时间排序
            sorted_tasks = sorted(
                [t for t in tasks if t.get("completed_at")],
                key=lambda t: t["completed_at"],
            )

            if len(sorted_tasks) >= 2:
                sequence = [t.get("task_type", "unknown") for t in sorted_tasks]
                gene = self._create_gene(
                    category="sequence",
                    name=f"任务序列: {pid}",
                    description=f"项目 {pid} 中的任务执行顺序: {' -> '.join(sequence)}",
                    conditions={"project_id": pid},
                    action={"sequence": sequence},
                    strategy=[{"action": "execute_sequence", "value": sequence}],
                    preconditions=[f"project_id=={pid}"],
                    signals_match=[f"project:{pid}"],
                    support_count=1,
                    confidence=0.5,  # 单次观察，低置信度
                    source_task_ids=[t.get("task_id", "") for t in sorted_tasks],
                    tags=["sequence", "ordering"],
                )
                genes.append(gene)

        return genes

    def _create_gene(self, **kwargs) -> Gene:
        self._rule_counter += 1

        # 从 kwargs 中提取兼容字段
        name = kwargs.pop("name", "")
        description = kwargs.pop("description", "")
        conditions = kwargs.pop("conditions", {})
        action = kwargs.pop("action", {})
        support_count = kwargs.pop("support_count", 0)
        confidence = kwargs.pop("confidence", 0.0)
        source_task_ids = kwargs.pop("source_task_ids", [])
        tags = kwargs.pop("tags", [])

        # 添加 epigenetic_marks
        epigenetic_marks = kwargs.pop("epigenetic_marks", [])
        if confidence > 0:
            epigenetic_marks.append(EpigeneticMark(
                mark="score",
                value=confidence,
                timestamp=datetime.now().isoformat(),
            ))

        gene_id = kwargs.get("id", f"gene-{self._rule_counter:04d}")
        if not kwargs.get("id"):
            kwargs["id"] = gene_id

        gene = Gene(
            _name=name,
            _description=description,
            _support_count=support_count,
            _confidence=confidence,
            _source_task_ids=source_task_ids,
            _tags=tags,
            _conditions=conditions,
            _action=action,
            epigenetic_marks=epigenetic_marks,
            **kwargs,
        )
        return gene
