"""
Evo - 权重更新器 (Weight Updater)

将 Evo 进化结果应用到匹配引擎和 Agent 能力权重。

职责：
1. 将固化记忆体的权重调整应用到 Agent 能力权重
2. 将分析器的采纳结果应用到任务匹配引擎
3. 提供权重回滚机制

GEP 协议映射:
  WeightUpdate        →  EvolutionEvent
  apply_patterns()    →  接收 List[Capsule] 而不是 List[SolidifiedPattern]
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from evo.gep_protocol import Capsule, EvolutionEvent
from evo.distillation.solidify import PatternStatus
from evo.mutation.analyzer import AnalysisReport, AdoptionDecision
from evo.mutation.mutation import Mutation

logger = logging.getLogger(__name__)


class WeightUpdater:
    """
    Evo 权重更新器（原 WeightUpdate → EvolutionEvent）

    用法：
        updater = WeightUpdater()
        # 从固化记忆体更新
        events = updater.apply_patterns(capsules)
        # 从突变分析结果更新
        events = updater.apply_analysis(report, mutation)
    """

    def __init__(self):
        self._events: List[EvolutionEvent] = []
        self._event_counter = 0
        # 当前权重快照
        self._agent_weights: Dict[str, Dict[str, float]] = {}  # agent_id -> {tag: weight}
        self._matching_weights: Dict[str, float] = {}          # capability_tag -> weight

    def set_agent_weights(self, agent_id: str, weights: Dict[str, float]) -> None:
        """设置 Agent 当前权重快照"""
        self._agent_weights[agent_id] = dict(weights)

    def set_matching_weight(self, tag: str, weight: float) -> None:
        """设置匹配权重"""
        self._matching_weights[tag] = weight

    def apply_patterns(
        self,
        capsules: List[Capsule],
        agent_id: Optional[str] = None,
    ) -> List[EvolutionEvent]:
        """
        将固化记忆体的权重调整应用到 Agent。

        Args:
            capsules: 已固化的 Capsule 列表
            agent_id: 可选，只更新指定 Agent

        Returns:
            EvolutionEvent 列表（原 WeightUpdate）
        """
        events = []

        for capsule in capsules:
            # 检查状态 — 只应用 SOLIDIFIED 或 VALIDATED
            status = capsule._status
            if status not in (PatternStatus.SOLIDIFIED.value, PatternStatus.VALIDATED.value):
                continue

            # 从 Capsule 的 weight_adjustments 或 epigenetic_marks 提取权重调整
            weight_adjustments = capsule.weight_adjustments
            if not weight_adjustments:
                continue

            if agent_id:
                # 只更新指定 Agent
                events.extend(
                    self._apply_to_agent(agent_id, capsule)
                )
            else:
                # 更新所有 Agent
                for aid in self._agent_weights:
                    events.extend(
                        self._apply_to_agent(aid, capsule)
                    )

            # 同时更新全局匹配权重
            events.extend(
                self._apply_to_matching(capsule)
            )

        logger.info(
            "Applied %d pattern updates from %d capsules",
            len(events), len(capsules),
        )
        return events

    def apply_analysis(
        self,
        report: AnalysisReport,
        mutation: Mutation,
    ) -> List[EvolutionEvent]:
        """
        将突变分析结果应用到权重（输出 EvolutionEvent）。

        Args:
            report: 分析报告
            mutation: 突变对象

        Returns:
            EvolutionEvent 列表
        """
        events = []

        if report.decision == AdoptionDecision.ACCEPT:
            # 采纳 → 应用突变后的权重
            if mutation.mutation_type.value == "weight_adjust":
                for tag, new_weight in mutation.after.items():
                    old_weight = mutation.before.get(tag, 1.0)
                    if isinstance(new_weight, (int, float)):
                        event = self._create_event(
                            intent="optimize",
                            target_type="agent_weight",
                            target_id=mutation.target_id,
                            field_name=tag,
                            old_value=old_weight,
                            new_value=float(new_weight),
                            source=mutation.mutation_id,
                            capsule_id=None,
                            mutation_id=mutation.mutation_id,
                        )
                        events.append(event)

                        # 更新快照
                        if mutation.target_id in self._agent_weights:
                            self._agent_weights[mutation.target_id][tag] = float(new_weight)

            elif mutation.mutation_type.value == "parameter_tweak":
                for key, new_value in mutation.after.items():
                    old_value = mutation.before.get(key, 0)
                    if isinstance(new_value, (int, float)) and key != "id":
                        event = self._create_event(
                            intent="optimize",
                            target_type="matching_weight",
                            target_id=mutation.target_id,
                            field_name=key,
                            old_value=float(old_value),
                            new_value=float(new_value),
                            source=mutation.mutation_id,
                            capsule_id=None,
                            mutation_id=mutation.mutation_id,
                        )
                        events.append(event)
                        self._matching_weights[key] = float(new_value)

        elif report.decision == AdoptionDecision.ROLLBACK:
            # 回滚 → 恢复突变前的权重
            for key, old_value in mutation.before.items():
                if isinstance(old_value, (int, float)):
                    current = mutation.after.get(key, old_value)
                    event = self._create_event(
                        intent="repair",
                        target_type="agent_weight" if mutation.target_type == "agent" else "matching_weight",
                        target_id=mutation.target_id,
                        field_name=key,
                        old_value=float(current),
                        new_value=float(old_value),
                        source=f"rollback:{mutation.mutation_id}",
                        capsule_id=None,
                        mutation_id=mutation.mutation_id,
                    )
                    events.append(event)

        elif report.decision == AdoptionDecision.TRIAL:
            # 试用 → 轻量调整（减半幅度）
            if mutation.mutation_type.value == "weight_adjust":
                for tag, new_weight in mutation.after.items():
                    old_weight = mutation.before.get(tag, 1.0)
                    if isinstance(new_weight, (int, float)):
                        trial_weight = old_weight + (new_weight - old_weight) * 0.5
                        event = self._create_event(
                            intent="optimize",
                            target_type="agent_weight",
                            target_id=mutation.target_id,
                            field_name=tag,
                            old_value=old_weight,
                            new_value=round(trial_weight, 4),
                            source=f"trial:{mutation.mutation_id}",
                            capsule_id=None,
                            mutation_id=mutation.mutation_id,
                        )
                        events.append(event)

        logger.info(
            "Applied %d weight events from analysis of %s (decision=%s)",
            len(events), mutation.mutation_id, report.decision.value,
        )
        return events

    def get_events(self, target_id: Optional[str] = None) -> List[EvolutionEvent]:
        """获取进化事件记录"""
        events = self._events
        if target_id:
            events = [e for e in events if e.target_id == target_id]
        return events

    # 向后兼容别名
    def get_updates(self, target_id: Optional[str] = None) -> List[EvolutionEvent]:
        """向后兼容: 获取进化事件（原 get_updates）"""
        return self.get_events(target_id)

    def revert_event(self, event_id: str) -> bool:
        """回滚单个权重更新"""
        for event in self._events:
            if event.id == event_id and not event.reverted:
                # 交换 old 和 new
                event._old_value, event._new_value = event._new_value, event._old_value
                event.meta["reverted"] = True
                event.meta["reverted_at"] = datetime.now().isoformat()
                logger.info("Event %s reverted", event_id)
                return True
        return False

    # 向后兼容别名
    def revert_update(self, update_id: str) -> bool:
        """向后兼容: 回滚权重更新"""
        return self.revert_event(update_id)

    def get_current_agent_weights(self, agent_id: str) -> Dict[str, float]:
        """获取 Agent 当前权重"""
        return dict(self._agent_weights.get(agent_id, {}))

    def get_current_matching_weights(self) -> Dict[str, float]:
        """获取当前匹配权重"""
        return dict(self._matching_weights)

    def get_current_all_weights(self) -> Dict[str, Dict[str, float]]:
        """获取所有 Agent 和全局的当前权重"""
        result = dict(self._agent_weights)
        if self._matching_weights:
            result["_global"] = dict(self._matching_weights)
        return result

    # ---------- 内部方法 ----------

    def _apply_to_agent(
        self,
        agent_id: str,
        capsule: Capsule,
    ) -> List[EvolutionEvent]:
        """将记忆体的权重调整应用到指定 Agent"""
        events = []
        current = self._agent_weights.get(agent_id, {})

        for tag, delta in capsule.weight_adjustments.items():
            old_weight = current.get(tag, 1.0)
            new_weight = round(old_weight + delta, 4)

            event = self._create_event(
                intent="optimize",
                target_type="agent_weight",
                target_id=agent_id,
                field_name=tag,
                old_value=old_weight,
                new_value=new_weight,
                source=capsule.id,
                capsule_id=capsule.id,
                mutation_id="",
            )
            events.append(event)

            # 更新快照
            self._agent_weights.setdefault(agent_id, {})[tag] = new_weight

        return events

    def _apply_to_matching(self, capsule: Capsule) -> List[EvolutionEvent]:
        """将记忆体的权重调整应用到全局匹配权重"""
        events = []

        for tag, delta in capsule.weight_adjustments.items():
            old_weight = self._matching_weights.get(tag, 1.0)
            new_weight = round(old_weight + delta, 4)

            event = self._create_event(
                intent="optimize",
                target_type="matching_weight",
                target_id=tag,
                field_name=tag,
                old_value=old_weight,
                new_value=new_weight,
                source=capsule.id,
                capsule_id=capsule.id,
                mutation_id="",
            )
            events.append(event)

            self._matching_weights[tag] = new_weight

        return events

    def _create_event(
        self,
        intent: str,
        target_type: str,
        target_id: str,
        field_name: str,
        old_value: float,
        new_value: float,
        source: str,
        capsule_id: Optional[str],
        mutation_id: str,
    ) -> EvolutionEvent:
        self._event_counter += 1
        event = EvolutionEvent(
            id=f"evo-{self._event_counter:06d}",
            intent=intent,
            mutation_id=mutation_id,
            capsule_id=capsule_id,
            outcome={
                "status": "applied",
                "old_value": old_value,
                "new_value": new_value,
            },
            blast_radius={
                "target_type": target_type,
                "field": field_name,
            },
            meta={
                "source": source,
            },
            # 兼容 WeightUpdate 字段
            _target_type=target_type,
            _target_id=target_id,
            _field_name=field_name,
            _old_value=old_value,
            _new_value=new_value,
            _source=source,
        )
        self._events.append(event)
        return event
