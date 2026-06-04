"""
Evo - 突变器 (Mutation)

实现任务/策略变异逻辑，模拟进化算法中的突变操作。

突变类型：
- 能力标签变异：调整 Agent 能力权重
- 策略变异：改变任务分配策略
- 参数变异：调整执行参数
- 交叉变异：结合两个策略的优点
"""

import copy
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MutationType(str, Enum):
    """突变类型"""
    WEIGHT_ADJUST = "weight_adjust"     # 权重调整
    CAPABILITY_SWAP = "capability_swap"  # 能力替换
    PARAMETER_TWEAK = "parameter_tweak"  # 参数微调
    CROSSOVER = "crossover"              # 交叉
    RANDOM = "random"                    # 随机突变


@dataclass
class Mutation:
    """突变操作"""
    mutation_id: str
    mutation_type: MutationType
    target_id: str  # 目标 Agent ID 或策略 ID
    target_type: str  # "agent" | "strategy" | "pattern"
    # 变更内容
    before: Dict[str, Any]
    after: Dict[str, Any]
    # 元数据
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "mutation_type": self.mutation_type.value,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "before": self.before,
            "after": self.after,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class MutationResult:
    """突变结果"""
    mutation: Mutation
    applied: bool = False
    outcome_score: float = 0.0  # 突变后的效果评分 (-1 ~ 1)
    evaluation_notes: str = ""
    evaluated_at: Optional[datetime] = None


class Mutator:
    """
    突变器

    用法：
        mutator = Mutator()
        mutations = mutator.mutate(agent_state, context)
    """

    # 突变参数
    WEIGHT_MUTATION_RANGE = 0.15     # 权重调整幅度 ±15%
    PARAMETER_MUTATION_RANGE = 0.1   # 参数调整幅度 ±10%
    CROSSOVER_RATE = 0.3             # 交叉概率
    MUTATION_RATE = 0.1              # 随机突变概率

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._mutations: Dict[str, Mutation] = {}
        self._mutation_counter = 0

    def mutate_agent_capabilities(
        self,
        agent_id: str,
        current_capabilities: Dict[str, List[str]],
        context: Dict[str, Any],
    ) -> List[Mutation]:
        """
        对 Agent 能力进行突变。

        Args:
            agent_id: Agent ID
            current_capabilities: 当前能力 {dimension: [tags]}
            context: 上下文（任务历史、性能指标等）

        Returns:
            生成的突变列表
        """
        mutations = []

        # 1. 权重调整突变
        weight_mut = self._mutate_weights(agent_id, current_capabilities, context)
        if weight_mut:
            mutations.append(weight_mut)

        # 2. 能力替换突变
        if self._rng.random() < 0.2:  # 20% 概率
            swap_mut = self._mutate_capability_swap(agent_id, current_capabilities, context)
            if swap_mut:
                mutations.append(swap_mut)

        return mutations

    def mutate_strategy(
        self,
        strategy_id: str,
        current_strategy: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[Mutation]:
        """
        对任务分配策略进行突变。

        Args:
            strategy_id: 策略 ID
            current_strategy: 当前策略配置
            context: 上下文

        Returns:
            生成的突变列表
        """
        mutations = []

        # 1. 参数微调
        param_mut = self._mutate_parameters(strategy_id, current_strategy, context)
        if param_mut:
            mutations.append(param_mut)

        # 2. 随机突变
        if self._rng.random() < self.MUTATION_RATE:
            random_mut = self._mutate_random(strategy_id, current_strategy)
            if random_mut:
                mutations.append(random_mut)

        return mutations

    def crossover_strategies(
        self,
        strategy_a: Dict[str, Any],
        strategy_b: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Mutation]:
        """
        交叉两个策略。

        Args:
            strategy_a: 策略 A
            strategy_b: 策略 B
            context: 上下文

        Returns:
            交叉突变（如果有）
        """
        if self._rng.random() > self.CROSSOVER_RATE:
            return None

        # 随机选择每个字段来自哪个父策略
        all_keys = set(list(strategy_a.keys()) + list(strategy_b.keys()))
        child = {}
        for key in all_keys:
            if key in strategy_a and key in strategy_b:
                child[key] = self._rng.choice([strategy_a[key], strategy_b[key]])
            elif key in strategy_a:
                child[key] = strategy_a[key]
            else:
                child[key] = strategy_b[key]

        self._mutation_counter += 1
        mutation = Mutation(
            mutation_id=f"mut-{self._mutation_counter:06d}",
            mutation_type=MutationType.CROSSOVER,
            target_id="crossover",
            target_type="strategy",
            before={"strategy_a": strategy_a, "strategy_b": strategy_b},
            after={"child": child},
            description=f"交叉两个策略，生成子策略（{len(all_keys)} 个字段）",
            metadata={"crossover_keys": list(all_keys)},
        )
        self._mutations[mutation.mutation_id] = mutation
        return mutation

    def get_mutation(self, mutation_id: str) -> Optional[Mutation]:
        return self._mutations.get(mutation_id)

    def list_mutations(self, target_id: Optional[str] = None) -> List[Mutation]:
        mutations = list(self._mutations.values())
        if target_id:
            mutations = [m for m in mutations if m.target_id == target_id]
        return mutations

    # ---------- 内部突变方法 ----------

    def _mutate_weights(
        self,
        agent_id: str,
        capabilities: Dict[str, List[str]],
        context: Dict[str, Any],
    ) -> Optional[Mutation]:
        """权重调整突变"""
        weights = context.get("current_weights", {})
        if not weights:
            return None

        before = dict(weights)
        after = {}

        for tag, weight in weights.items():
            # 根据性能调整权重
            performance = context.get("tag_performance", {}).get(tag, 0.5)
            if performance > 0.7:
                # 表现好 → 增加权重
                delta = self._rng.uniform(0, self.WEIGHT_MUTATION_RANGE)
                after[tag] = min(weight + delta, 2.0)
            elif performance < 0.3:
                # 表现差 → 减少权重
                delta = self._rng.uniform(0, self.WEIGHT_MUTATION_RANGE)
                after[tag] = max(weight - delta, 0.1)
            else:
                after[tag] = weight

        # 只有实际变化才生成突变
        if before != after:
            self._mutation_counter += 1
            mutation = Mutation(
                mutation_id=f"mut-{self._mutation_counter:06d}",
                mutation_type=MutationType.WEIGHT_ADJUST,
                target_id=agent_id,
                target_type="agent",
                before=before,
                after=after,
                description=f"基于性能调整 {len([k for k in before if before[k] != after.get(k)])} 个能力权重",
                metadata={"capabilities": capabilities},
            )
            self._mutations[mutation.mutation_id] = mutation
            return mutation

        return None

    def _mutate_capability_swap(
        self,
        agent_id: str,
        capabilities: Dict[str, List[str]],
        context: Dict[str, Any],
    ) -> Optional[Mutation]:
        """能力替换突变"""
        all_tags = []
        for dim, tags in capabilities.items():
            if isinstance(tags, list):
                all_tags.extend(tags)

        if len(all_tags) < 2:
            return None

        # 随机替换一个能力标签
        available = context.get("available_tags", [])
        if not available:
            return None

        old_tag = self._rng.choice(all_tags)
        new_tag = self._rng.choice(available)

        if old_tag == new_tag:
            return None

        self._mutation_counter += 1
        mutation = Mutation(
            mutation_id=f"mut-{self._mutation_counter:06d}",
            mutation_type=MutationType.CAPABILITY_SWAP,
            target_id=agent_id,
            target_type="agent",
            before={"replaced_tag": old_tag},
            after={"new_tag": new_tag},
            description=f"能力替换: {old_tag} -> {new_tag}",
            metadata={"current_capabilities": capabilities},
        )
        self._mutations[mutation.mutation_id] = mutation
        return mutation

    def _mutate_parameters(
        self,
        strategy_id: str,
        strategy: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Mutation]:
        """参数微调突变"""
        numeric_params = {
            k: v for k, v in strategy.items()
            if isinstance(v, (int, float)) and k not in ("id", "version")
        }

        if not numeric_params:
            return None

        before = dict(strategy)
        after = dict(strategy)

        # 随机调整 1-2 个参数
        params_to_mutate = self._rng.sample(
            list(numeric_params.keys()),
            min(2, len(numeric_params)),
        )

        for param in params_to_mutate:
            current = strategy[param]
            delta = current * self._rng.uniform(-self.PARAMETER_MUTATION_RANGE, self.PARAMETER_MUTATION_RANGE)
            after[param] = round(current + delta, 4)

        if before != after:
            self._mutation_counter += 1
            changed = [k for k in before if before[k] != after.get(k)]
            mutation = Mutation(
                mutation_id=f"mut-{self._mutation_counter:06d}",
                mutation_type=MutationType.PARAMETER_TWEAK,
                target_id=strategy_id,
                target_type="strategy",
                before=before,
                after=after,
                description=f"微调 {len(changed)} 个参数: {changed}",
                metadata={"changed_params": changed},
            )
            self._mutations[mutation.mutation_id] = mutation
            return mutation

        return None

    def _mutate_random(
        self,
        strategy_id: str,
        strategy: Dict[str, Any],
    ) -> Optional[Mutation]:
        """随机突变"""
        if not strategy:
            return None

        key = self._rng.choice(list(strategy.keys()))
        value = strategy[key]

        if isinstance(value, (int, float)):
            new_value = value * self._rng.uniform(0.5, 1.5)
        elif isinstance(value, bool):
            new_value = not value
        else:
            return None

        after = dict(strategy)
        after[key] = new_value

        self._mutation_counter += 1
        mutation = Mutation(
            mutation_id=f"mut-{self._mutation_counter:06d}",
            mutation_type=MutationType.RANDOM,
            target_id=strategy_id,
            target_type="strategy",
            before={key: value},
            after={key: new_value},
            description=f"随机突变: {key} {value} -> {new_value}",
        )
        self._mutations[mutation.mutation_id] = mutation
        return mutation
