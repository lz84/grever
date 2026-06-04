"""
Evo (进化) - Agent 验证、纠错和进化

提供智能体能力进化、验证纠错和自适应机制

GEP 协议 (Genome Evolution Protocol):
- Gene: 可复用技能/策略的标准化描述
- Capsule: 一次完整执行过程的记录
- EvolutionEvent: 进化过程的元数据记录

子模块：
- distillation: 从成功/失败任务提取基因并固化为记忆体
- mutation: 任务/策略变异逻辑
- weight: 权重更新（输出 EvolutionEvent）
- a2a: Agent-to-Agent 通信协议
"""

from evo.gep_protocol import Gene, Capsule, EvolutionEvent, EpigeneticMark
from evo.distillation.distiller import RuleDistiller
from evo.distillation.solidify import Solidifier, PatternStatus
from evo.mutation.mutation import Mutator
from evo.mutation.analyzer import MutationAnalyzer
from evo.a2a.a2a import A2AProtocol
from evo.weight.weight_updater import WeightUpdater

__all__ = [
    # GEP 协议核心类
    "Gene",
    "Capsule",
    "EvolutionEvent",
    "EpigeneticMark",
    # 蒸馏 & 固化
    "RuleDistiller",
    "Solidifier",
    "PatternStatus",
    # 变异
    "Mutator",
    "MutationAnalyzer",
    # A2A
    "A2AProtocol",
    # 权重
    "WeightUpdater",
]
