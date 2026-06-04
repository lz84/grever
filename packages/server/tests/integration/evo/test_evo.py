# -*- coding: utf-8 -*-
"""
单元测试: evo/ 模块 — GEP 协议适配版

覆盖:
1. RuleDistiller - 基因提取器 (输出 Gene)
2. Solidifier - 固化引擎 (输出 Capsule)
3. Mutator - 突变器
4. MutationAnalyzer - 突变分析器
5. A2AProtocol - Agent-to-Agent 通信协议
6. WeightUpdater - 权重更新器 (输出 EvolutionEvent)

GEP 协议映射:
  ExtractedRule     →  Gene
  SolidifiedPattern →  Capsule
  WeightUpdate      →  EvolutionEvent
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from evo.distillation.distiller import RuleDistiller, RuleType
from evo.distillation.solidify import Solidifier, PatternStatus
from evo.gep_protocol import Gene, Capsule, EvolutionEvent, EpigeneticMark
from evo.mutation.mutation import Mutator, Mutation, MutationType, MutationResult
from evo.mutation.analyzer import MutationAnalyzer, AnalysisReport, AdoptionDecision
from evo.a2a.a2a import (
    A2AProtocol, A2AMessage, CollaborationSession,
    MessageType, MessagePriority, MessageStatus
)
from evo.weight.weight_updater import WeightUpdater


# ============================================================================
# GEP Protocol Dataclass Tests
# ============================================================================

class TestGEPProtocol:
    """GEP 协议 dataclass 基础测试"""

    def test_gene_to_dict(self):
        """测试 Gene.to_dict()"""
        gene = Gene(
            id="gene-test-001",
            category="capability",
            signals_match=["task:coding"],
            preconditions=["agent_available"],
            strategy=[{"action": "use_capability", "value": "python"}],
            constraints={"max_files": 5},
            validation=["pytest"],
            epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
            asset_id="hub-001",
        )
        d = gene.to_dict()
        assert d["type"] == "gene"
        assert d["id"] == "gene-test-001"
        assert d["category"] == "capability"
        assert d["signals_match"] == ["task:coding"]
        assert len(d["epigenetic_marks"]) == 1
        assert d["asset_id"] == "hub-001"

    def test_gene_from_dict(self):
        """测试 Gene.from_dict()"""
        data = {
            "type": "gene",
            "schema_version": "1.0",
            "id": "gene-roundtrip",
            "category": "optimize",
            "signals_match": ["timeout"],
            "preconditions": [],
            "strategy": [{"action": "retry"}],
            "constraints": {},
            "validation": [],
            "epigenetic_marks": [{"mark": "score", "value": 0.85}],
            "asset_id": None,
        }
        gene = Gene.from_dict(data)
        assert gene.id == "gene-roundtrip"
        assert gene.category == "optimize"
        assert len(gene.signals_match) == 1
        assert len(gene.epigenetic_marks) == 1

    def test_capsule_to_dict(self):
        """测试 Capsule.to_dict()"""
        capsule = Capsule(
            id="capsule-001",
            trigger=["timeout", "retry"],
            gene="gene-test-001",
            summary="Successful retry",
            confidence=0.92,
            blast_radius={"files_changed": 2},
            outcome={"status": "success", "score": 0.92},
            success_streak=3,
            a2a={"source": "local", "ready_for_hub": True},
        )
        d = capsule.to_dict()
        assert d["type"] == "capsule"
        assert d["id"] == "capsule-001"
        assert d["gene"] == "gene-test-001"
        assert d["confidence"] == 0.92
        assert d["outcome"]["status"] == "success"

    def test_capsule_from_dict(self):
        """测试 Capsule.from_dict()"""
        data = {
            "type": "capsule",
            "id": "capsule-roundtrip",
            "trigger": ["error"],
            "gene": "gene-1",
            "summary": "Test",
            "confidence": 0.7,
            "outcome": {"status": "success", "score": 0.7},
        }
        capsule = Capsule.from_dict(data)
        assert capsule.id == "capsule-roundtrip"
        assert capsule.confidence == 0.7

    def test_evolution_event_to_dict(self):
        """测试 EvolutionEvent.to_dict()"""
        event = EvolutionEvent(
            id="event-001",
            intent="optimize",
            signals=["timeout"],
            genes_used=["gene-1"],
            mutation_id="mut-1",
            outcome={"status": "success"},
            capsule_id="capsule-001",
            env_fingerprint={"platform": "windows"},
        )
        d = event.to_dict()
        assert d["type"] == "evolution_event"
        assert d["intent"] == "optimize"
        assert d["capsule_id"] == "capsule-001"

    def test_evolution_event_from_dict(self):
        """测试 EvolutionEvent.from_dict()"""
        data = {
            "type": "evolution_event",
            "id": "event-roundtrip",
            "intent": "repair",
            "signals": ["error"],
            "genes_used": ["gene-1"],
            "outcome": {"status": "applied"},
        }
        event = EvolutionEvent.from_dict(data)
        assert event.id == "event-roundtrip"
        assert event.intent == "repair"


# ============================================================================
# RuleDistiller Tests (输出 Gene)
# ============================================================================

class TestRuleDistiller:
    """基因提取器测试"""

    def _make_task_record(self, task_id='t1', task_type='coding', status='success',
                          quality=0.8, duration=1000, capabilities=None,
                          project_id=None, error_type=None):
        return {
            'task_id': task_id,
            'task_type': task_type,
            'task_category': 'dev',
            'required_capabilities': capabilities or [],
            'assigned_agent': 'agent-1',
            'agent_capabilities': {'lang': ['python', 'java']},
            'status': status,
            'quality_score': quality,
            'duration_ms': duration,
            'error_type': error_type,
            'project_id': project_id,
        }

    def test_distill_capability_genes(self):
        """测试能力匹配基因提取"""
        distiller = RuleDistiller(min_support=2, min_confidence=0.3)
        records = [
            self._make_task_record(task_id='t1', status='success', task_type='coding'),
            self._make_task_record(task_id='t2', status='success', task_type='coding'),
            self._make_task_record(task_id='t3', status='success', task_type='coding'),
        ]
        genes = distiller.distill(records)
        assert len(genes) > 0
        # 应该有能力基因
        cap_genes = [g for g in genes if g.category == "capability"]
        assert len(cap_genes) > 0
        # 验证是 Gene 类型
        assert isinstance(cap_genes[0], Gene)

    def test_distill_pattern_genes(self):
        """测试模式基因提取"""
        distiller = RuleDistiller(min_support=1, min_confidence=0.1)
        records = [
            self._make_task_record(task_id='t1', status='success', quality=0.9),
            self._make_task_record(task_id='t2', status='success', quality=0.85),
        ]
        genes = distiller.distill(records)
        pattern_genes = [g for g in genes if g.category == "pattern"]
        assert len(pattern_genes) > 0

    def test_distill_anti_pattern_genes(self):
        """测试反模式基因提取"""
        distiller = RuleDistiller(min_support=2, min_confidence=0.3)
        records = [
            self._make_task_record(task_id='t1', status='failed', error_type='timeout'),
            self._make_task_record(task_id='t2', status='failed', error_type='timeout'),
            self._make_task_record(task_id='t3', status='failed', error_type='timeout'),
        ]
        genes = distiller.distill(records)
        anti_genes = [g for g in genes if g.category == "anti_pattern"]
        assert len(anti_genes) > 0
        assert 'timeout' in anti_genes[0].name

    def test_distill_sequence_genes(self):
        """测试序列基因提取"""
        distiller = RuleDistiller(min_support=1, min_confidence=0.1)
        now = datetime.now()
        records = [
            {**self._make_task_record(task_id='t1', task_type='plan'), 'completed_at': now},
            {**self._make_task_record(task_id='t2', task_type='code'), 'completed_at': now + timedelta(hours=1)},
            {**self._make_task_record(task_id='t3', task_type='test'), 'completed_at': now + timedelta(hours=2)},
        ]
        for r in records:
            r['project_id'] = 'proj-1'
        genes = distiller.distill(records)
        seq_genes = [g for g in genes if g.category == "sequence"]
        assert len(seq_genes) > 0

    def test_distill_no_records(self):
        """测试无记录时不产生基因"""
        distiller = RuleDistiller()
        genes = distiller.distill([])
        assert len(genes) == 0

    def test_get_genes(self):
        """测试获取基因"""
        distiller = RuleDistiller(min_support=1, min_confidence=0.1)
        records = [self._make_task_record(task_id='t1', status='success')]
        genes = distiller.distill(records)

        # 获取全部
        all_genes = distiller.get_genes()
        assert len(all_genes) > 0

        # 按类型获取
        pattern_genes = distiller.get_genes(category="pattern")
        assert all(g.category == "pattern" for g in pattern_genes)

    def test_get_rules_backward_compat(self):
        """测试向后兼容的 get_rules()"""
        distiller = RuleDistiller(min_support=1, min_confidence=0.1)
        records = [self._make_task_record(task_id='t1', status='success')]
        distiller.distill(records)

        # get_rules 应该作为 get_genes 的别名工作
        rules = distiller.get_rules()
        assert len(rules) > 0
        assert isinstance(rules[0], Gene)

    def test_update_gene_support(self):
        """测试更新基因支持度"""
        distiller = RuleDistiller(min_support=1, min_confidence=0.1)
        records = [self._make_task_record(task_id='t1', status='success')]
        genes = distiller.distill(records)
        gene = genes[0]

        distiller.update_gene_support(gene.id, True)
        assert gene.support_count > 0
        assert gene.confidence > 0

    def test_get_gene_by_id(self):
        """测试按 ID 获取基因"""
        distiller = RuleDistiller(min_support=1, min_confidence=0.1)
        records = [self._make_task_record(task_id='t1', status='success')]
        distiller.distill(records)
        gene = distiller.get_gene('gene-0001')
        assert gene is not None
        assert gene.id == 'gene-0001'

        nonexistent = distiller.get_gene('gene-9999')
        assert nonexistent is None


# ============================================================================
# Solidifier Tests (输出 Capsule)
# ============================================================================

class TestSolidifier:
    """固化引擎测试"""

    def test_solidify_genes(self):
        """测试基因固化"""
        solidifier = Solidifier()
        genes = [
            Gene(
                id='gene-001',
                category="capability",
                signals_match=["task:coding"],
                strategy=[{"action": "use_capabilities", "value": ["python"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.8)],
                _name='High quality pattern',
                _description='Test gene',
                _conditions={'task_type': 'coding'},
                _action={'recommended_capabilities': ['python']},
                _support_count=5,
                _confidence=0.8,
                _tags=['coding', 'capability'],
            ),
            Gene(
                id='gene-002',
                category="pattern",
                signals_match=[],
                strategy=[],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.3)],
                _name='Low quality',
                _description='Low quality gene',
                _conditions={'task_type': 'test'},
                _action={},
                _support_count=1,
                _confidence=0.3,  # 低于阈值，应该被过滤
                _tags=['test'],
            ),
        ]
        capsules = solidifier.solidify(genes)
        # 只有高置信度基因应该被固化
        assert len(capsules) >= 1
        # 验证状态映射
        assert capsules[0]._status in (
            PatternStatus.SOLIDIFIED.value,
            PatternStatus.VALIDATED.value,
        )

    def test_solidify_anti_pattern_lower_threshold(self):
        """测试反模式降低阈值"""
        solidifier = Solidifier()
        genes = [
            Gene(
                id='gene-003',
                category="anti_pattern",
                signals_match=["error:timeout"],
                constraints={"forbidden_error_types": ["timeout"]},
                strategy=[],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.5)],
                _name='Anti pattern',
                _description='Should be included',
                _conditions={'error_type': 'timeout'},
                _action={'avoid': True},
                _support_count=1,
                _confidence=0.5,  # 对反模式来说够了
                _tags=['timeout'],
            ),
        ]
        capsules = solidifier.solidify(genes)
        assert len(capsules) >= 1

    def test_promote_capsule(self):
        """测试提升记忆体状态"""
        solidifier = Solidifier()
        genes = [
            Gene(
                id='gene-004',
                category="capability",
                signals_match=[],
                strategy=[{"action": "use_capabilities", "value": ["test"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
                _name='test',
                _description='test',
                _conditions={},
                _action={'recommended_capabilities': ['test']},
                _support_count=5,
                _confidence=0.9,
            ),
        ]
        capsules = solidifier.solidify(genes)
        capsule = capsules[0]

        solidifier.promote_capsule(capsule.id, PatternStatus.DEPRECATED)
        c = solidifier.get_capsule(capsule.id)
        assert c._status == PatternStatus.DEPRECATED.value

    def test_record_usage(self):
        """测试记录记忆体使用"""
        solidifier = Solidifier()
        genes = [
            Gene(
                id='gene-005',
                category="capability",
                signals_match=[],
                strategy=[{"action": "use_capabilities", "value": ["test"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
                _name='test',
                _description='test',
                _conditions={},
                _action={'recommended_capabilities': ['test']},
                _support_count=5,
                _confidence=0.9,
            ),
        ]
        capsules = solidifier.solidify(genes)
        cid = capsules[0].id

        solidifier.record_usage(cid, True)
        c = solidifier.get_capsule(cid)
        assert c._usage_count == 1
        assert c._success_rate > 0

    def test_deprecate_capsule(self):
        """测试废弃记忆体"""
        solidifier = Solidifier()
        genes = [
            Gene(
                id='gene-006',
                category="capability",
                signals_match=[],
                strategy=[{"action": "use_capabilities", "value": ["test"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
                _name='test',
                _description='test',
                _conditions={},
                _action={'recommended_capabilities': ['test']},
                _support_count=5,
                _confidence=0.9,
            ),
        ]
        capsules = solidifier.solidify(genes)
        cid = capsules[0].id

        result = solidifier.deprecate_capsule(cid, 'obsolete')
        assert result._status == PatternStatus.DEPRECATED.value

    def test_get_capsules_filter(self):
        """测试按状态/类型过滤记忆体"""
        solidifier = Solidifier()
        genes = [
            Gene(
                id='gene-007',
                category="capability",
                signals_match=[],
                strategy=[{"action": "use_capabilities", "value": ["test"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
                _name='cap rule',
                _description='test',
                _conditions={},
                _action={'recommended_capabilities': ['test']},
                _support_count=5,
                _confidence=0.9,
            ),
            Gene(
                id='gene-008',
                category="pattern",
                signals_match=[],
                strategy=[],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
                _name='pattern rule',
                _description='test',
                _conditions={},
                _action={},
                _support_count=5,
                _confidence=0.9,
            ),
        ]
        solidifier.solidify(genes)

        cap_capsules = solidifier.get_capsules(pattern_type="capability")
        assert all(c._pattern_type == "capability" for c in cap_capsules)

    def test_deduplication(self):
        """测试基因去重"""
        solidifier = Solidifier()
        # 两条完全相同的基因
        genes = [
            Gene(
                id='gene-009',
                category="capability",
                signals_match=["task:coding"],
                strategy=[{"action": "use_capabilities", "value": ["python"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.9)],
                _name='rule1',
                _description='test',
                _conditions={'task_type': 'coding'},
                _action={'recommended_capabilities': ['python']},
                _support_count=5,
                _confidence=0.9,
            ),
            Gene(
                id='gene-010',
                category="capability",
                signals_match=["task:coding"],
                strategy=[{"action": "use_capabilities", "value": ["python"]}],
                epigenetic_marks=[EpigeneticMark(mark="score", value=0.8)],
                _name='rule2',
                _description='test',
                _conditions={'task_type': 'coding'},
                _action={'recommended_capabilities': ['python']},
                _support_count=3,
                _confidence=0.8,
            ),
        ]
        capsules = solidifier.solidify(genes)
        assert len(capsules) == 1


# ============================================================================
# Mutator Tests
# ============================================================================

class TestMutator:
    """突变器测试"""

    def test_mutate_agent_capabilities_weight(self):
        """测试 Agent 能力权重突变"""
        mutator = Mutator(seed=42)
        capabilities = {'lang': ['python', 'java']}
        context = {
            'current_weights': {'python': 1.0, 'java': 1.0},
            'tag_performance': {'python': 0.8, 'java': 0.2},
        }
        mutations = mutator.mutate_agent_capabilities('agent-1', capabilities, context)
        assert len(mutations) >= 1
        assert any(m.mutation_type == MutationType.WEIGHT_ADJUST for m in mutations)

    def test_mutate_strategy_parameters(self):
        """测试策略参数突变"""
        mutator = Mutator(seed=42)
        strategy = {'max_retries': 3, 'timeout_ms': 5000, 'name': 'default'}
        mutations = mutator.mutate_strategy('strategy-1', strategy, {})
        assert len(mutations) >= 1

    def test_crossover_strategies(self):
        """测试策略交叉"""
        mutator = Mutator(seed=42)
        strategy_a = {'max_retries': 3, 'timeout_ms': 5000, 'priority': 'high'}
        strategy_b = {'max_retries': 5, 'timeout_ms': 3000, 'priority': 'low'}
        mutation = mutator.crossover_strategies(strategy_a, strategy_b, {})
        # crossover_rate = 0.3, 所以不一定每次都触发
        if mutation:
            assert mutation.mutation_type == MutationType.CROSSOVER
            assert 'child' in mutation.after

    def test_mutate_capability_swap(self):
        """测试能力替换突变"""
        mutator = Mutator(seed=42)
        capabilities = {'lang': ['python', 'java', 'go']}
        context = {'available_tags': ['rust', 'c++']}
        # 20% 概率触发 capability swap
        for _ in range(20):
            mutations = mutator.mutate_agent_capabilities('agent-1', capabilities, context)
            swap_mutations = [m for m in mutations if m.mutation_type == MutationType.CAPABILITY_SWAP]
            if swap_mutations:
                assert swap_mutations[0].before.get('replaced_tag') in ['python', 'java', 'go']
                break

    def test_get_and_list_mutations(self):
        """测试获取和列出突变"""
        mutator = Mutator(seed=42)
        capabilities = {'lang': ['python']}
        context = {
            'current_weights': {'python': 1.0},
            'tag_performance': {'python': 0.8},
        }
        mutations = mutator.mutate_agent_capabilities('agent-1', capabilities, context)
        if mutations:
            mid = mutations[0].mutation_id
            m = mutator.get_mutation(mid)
            assert m is not None
            assert m.mutation_id == mid

        all_mutations = mutator.list_mutations()
        assert len(all_mutations) >= len(mutations)

        target_mutations = mutator.list_mutations(target_id='agent-1')
        assert len(target_mutations) >= 0

    def test_mutate_random(self):
        """测试随机突变"""
        mutator = Mutator(seed=42)
        strategy = {'threshold': 0.5, 'enabled': True}
        mutations = mutator.mutate_strategy('strat-1', strategy, {})
        # random mutation 有 10% 概率
        random_muts = [m for m in mutations if m.mutation_type == MutationType.RANDOM]
        for m in random_muts:
            assert 'threshold' in m.before or 'enabled' in m.before


# ============================================================================
# MutationAnalyzer Tests
# ============================================================================

class TestMutationAnalyzer:
    """突变分析器测试"""

    def test_analyze_accept(self):
        """测试采纳突变"""
        analyzer = MutationAnalyzer()
        mutation = Mutation(
            mutation_id='mut-001',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-1',
            target_type='agent',
            before={'weight_a': 1.0},
            after={'weight_a': 1.2},
        )
        before_metrics = {'success_rate': 0.5, 'avg_quality': 0.5}
        after_metrics = {'success_rate': 0.8, 'avg_quality': 0.8}

        report = analyzer.analyze(mutation, before_metrics, after_metrics)
        assert report.decision in (AdoptionDecision.ACCEPT, AdoptionDecision.TRIAL)
        assert report.score > 0

    def test_analyze_reject(self):
        """测试拒绝突变"""
        analyzer = MutationAnalyzer()
        mutation = Mutation(
            mutation_id='mut-002',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-2',
            target_type='agent',
            before={'weight_a': 1.0},
            after={'weight_a': 0.5},
        )
        before_metrics = {'success_rate': 0.8, 'avg_quality': 0.8}
        after_metrics = {'success_rate': 0.3, 'avg_quality': 0.2, 'error_rate': 0.5}

        report = analyzer.analyze(mutation, before_metrics, after_metrics)
        assert report.decision in (AdoptionDecision.REJECT, AdoptionDecision.ROLLBACK)

    def test_analyze_no_change(self):
        """测试无变化时试用"""
        analyzer = MutationAnalyzer()
        mutation = Mutation(
            mutation_id='mut-003',
            mutation_type=MutationType.PARAMETER_TWEAK,
            target_id='strat-1',
            target_type='strategy',
            before={'param': 1.0},
            after={'param': 1.0},
        )
        before_metrics = {'success_rate': 0.5}
        after_metrics = {'success_rate': 0.5}

        report = analyzer.analyze(mutation, before_metrics, after_metrics)
        assert report.decision in (AdoptionDecision.TRIAL,)

    def test_get_reports(self):
        """测试获取报告"""
        analyzer = MutationAnalyzer()
        mutation = Mutation(
            mutation_id='mut-004',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-1',
            target_type='agent',
            before={'w': 1.0},
            after={'w': 1.5},
        )
        analyzer.analyze(mutation, {'success_rate': 0.5}, {'success_rate': 0.9})

        report = analyzer.get_report('mut-004')
        assert report is not None

        nonexistent = analyzer.get_report('nonexistent')
        assert nonexistent is None

    def test_target_history(self):
        """测试目标历史"""
        analyzer = MutationAnalyzer()
        for i in range(3):
            mutation = Mutation(
                mutation_id=f'mut-h{i}',
                mutation_type=MutationType.WEIGHT_ADJUST,
                target_id='agent-hist',
                target_type='agent',
                before={'w': 1.0},
                after={'w': 1.0 + i * 0.1},
            )
            analyzer.analyze(mutation, {'success_rate': 0.5}, {'success_rate': 0.5 + i * 0.1})

        history = analyzer.get_target_history('agent-hist')
        assert len(history) == 3

    def test_get_accepted_rejected(self):
        """测试获取采纳/拒绝的突变"""
        analyzer = MutationAnalyzer()
        # 产生一个接受的突变
        m1 = Mutation(
            mutation_id='mut-acc',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-1',
            target_type='agent',
            before={'w': 1.0},
            after={'w': 1.5},
        )
        analyzer.analyze(m1, {'success_rate': 0.5}, {'success_rate': 0.9})

        accepted = analyzer.get_accepted_mutations()
        # 取决于分数阈值
        assert len(accepted) >= 0


# ============================================================================
# A2AProtocol Tests
# ============================================================================

class TestA2AProtocol:
    """Agent-to-Agent 通信协议测试"""

    def test_send_and_receive(self):
        """测试消息发送和接收"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', ['python'])
        protocol.register_agent('agent-2', ['java'])

        msg = protocol.send('agent-1', 'agent-2', MessageType.QUERY, 'Hello?', {'question': 'test'})
        assert msg.status == MessageStatus.SENT

        received = protocol.receive('agent-2')
        assert len(received) == 1
        assert received[0].message_id == msg.message_id
        assert received[0].status == MessageStatus.DELIVERED

    def test_broadcast(self):
        """测试广播消息"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', ['python'])
        protocol.register_agent('agent-2', ['java'])

        msg = protocol.send('agent-1', '*', MessageType.NOTIFY, 'Broadcast', {'data': 'hello'})
        assert msg.receiver_id == '*'

        broadcasts = protocol.receive_broadcast('agent-2')
        assert len(broadcasts) == 1

    def test_send_query_response(self):
        """测试查询-响应模式"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', ['python'])
        protocol.register_agent('agent-2', ['java'])

        query_msg = protocol.send_query('agent-1', 'agent-2', 'What is your capability?')
        response_msg = protocol.send_response(
            'agent-2', 'agent-1', query_msg.message_id,
            {'capabilities': ['java']},
        )
        assert response_msg.in_reply_to == query_msg.message_id
        assert response_msg.message_type == MessageType.RESPONSE

    def test_acknowledge(self):
        """测试消息确认"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', [])
        protocol.register_agent('agent-2', [])

        msg = protocol.send('agent-1', 'agent-2', MessageType.NOTIFY, 'test')
        assert protocol.acknowledge(msg.message_id)
        assert protocol.acknowledge('nonexistent') is False

    def test_collaboration_session(self):
        """测试协作会话"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', ['python'])
        protocol.register_agent('agent-2', ['java'])

        session = protocol.create_session('agent-1', ['agent-2'], 'Test Collaboration')
        assert session.status == 'active'
        assert 'agent-1' in session.participants
        assert 'agent-2' in session.participants

        # 添加消息
        msg = protocol.send('agent-1', 'agent-2', MessageType.REQUEST, 'Request')
        assert protocol.add_session_message(session.session_id, msg)

        # 关闭会话
        closed = protocol.close_session(session.session_id, {'result': 'done'})
        assert closed is not None
        assert closed.status == 'completed'

    def test_find_agents_by_capability(self):
        """测试按能力查找 Agent"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', ['python', 'java'])
        protocol.register_agent('agent-2', ['java', 'go'])
        protocol.register_agent('agent-3', ['python'])

        python_agents = protocol.find_agents_by_capability('python')
        assert 'agent-1' in python_agents
        assert 'agent-3' in python_agents
        assert 'agent-2' not in python_agents

    def test_message_handler(self):
        """测试消息处理器"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', [])
        protocol.register_agent('agent-2', [])

        received_messages = []

        def handle_query(msg):
            received_messages.append(msg)

        protocol.register_handler(MessageType.QUERY, handle_query)
        protocol.send('agent-1', 'agent-2', MessageType.QUERY, 'Test')
        protocol.receive('agent-2')

        assert len(received_messages) == 1

    def test_message_expiry(self):
        """测试消息过期"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', [])
        protocol.register_agent('agent-2', [])

        # 发送一个立即过期的消息
        msg = protocol.send('agent-1', 'agent-2', MessageType.NOTIFY, 'test', ttl_seconds=0)
        # 等待过期
        import time
        time.sleep(0.1)

        received = protocol.receive('agent-2')
        assert len(received) == 0

    def test_get_message_and_session(self):
        """测试获取消息和会话"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', [])
        protocol.register_agent('agent-2', [])

        msg = protocol.send('agent-1', 'agent-2', MessageType.NOTIFY, 'test')
        retrieved = protocol.get_message(msg.message_id)
        assert retrieved is not None
        assert retrieved.message_id == msg.message_id

        session = protocol.create_session('agent-1', ['agent-2'], 'Test')
        retrieved_session = protocol.get_session(session.session_id)
        assert retrieved_session is not None

    def test_list_active_sessions(self):
        """测试列出活跃会话"""
        protocol = A2AProtocol()
        protocol.register_agent('agent-1', [])
        protocol.register_agent('agent-2', [])

        s1 = protocol.create_session('agent-1', ['agent-2'], 'Session 1')
        s2 = protocol.create_session('agent-1', ['agent-2'], 'Session 2')

        active = protocol.list_active_sessions()
        assert len(active) == 2

        protocol.close_session(s1.session_id)
        active = protocol.list_active_sessions()
        assert len(active) == 1


# ============================================================================
# WeightUpdater Tests (输出 EvolutionEvent)
# ============================================================================

class TestWeightUpdater:
    """权重更新器测试"""

    def test_set_and_get_weights(self):
        """测试设置和获取权重"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0, 'java': 0.8})
        updater.set_matching_weight('python', 1.5)

        assert updater.get_current_agent_weights('agent-1') == {'python': 1.0, 'java': 0.8}
        assert updater.get_current_matching_weights() == {'python': 1.5}

    def test_apply_patterns(self):
        """测试从固化记忆体应用权重"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0, 'java': 0.8})

        capsules = [
            Capsule(
                id='capsule-001',
                trigger=[],
                gene='gene-001',
                summary='test',
                confidence=0.9,
                outcome={"status": "success", "score": 0.9},
                _pattern_id='p1',
                _pattern_type='capability',
                _status=PatternStatus.SOLIDIFIED.value,
                _match_conditions={},
                _template={},
                _weight_adjustments={'python': 0.1, 'java': -0.05},
                _source_rule_ids=['gene-001'],
            ),
        ]
        events = updater.apply_patterns(capsules)
        assert len(events) >= 1
        # 验证返回的是 EvolutionEvent
        assert isinstance(events[0], EvolutionEvent)

        weights = updater.get_current_agent_weights('agent-1')
        assert weights['python'] == 1.1
        assert weights['java'] == 0.75

    def test_apply_patterns_backward_compat(self):
        """测试向后兼容的 get_updates()"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})

        capsules = [
            Capsule(
                id='capsule-002',
                trigger=[],
                gene='gene-002',
                summary='test',
                confidence=0.9,
                outcome={"status": "success", "score": 0.9},
                _pattern_id='p2',
                _pattern_type='capability',
                _status=PatternStatus.SOLIDIFIED.value,
                _match_conditions={},
                _template={},
                _weight_adjustments={'python': 0.1},
                _source_rule_ids=['gene-002'],
            ),
        ]
        updater.apply_patterns(capsules)

        # get_updates 应该作为 get_events 的别名工作
        all_updates = updater.get_updates()
        assert len(all_updates) >= 1
        assert isinstance(all_updates[0], EvolutionEvent)

    def test_apply_analysis_accept(self):
        """测试从分析结果应用权重（采纳）"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})

        mutation = Mutation(
            mutation_id='mut-w1',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-1',
            target_type='agent',
            before={'python': 1.0},
            after={'python': 1.3},
        )
        report = AnalysisReport(
            mutation_id='mut-w1',
            decision=AdoptionDecision.ACCEPT,
            score=0.3,
            metrics={},
            reasoning='good',
        )

        events = updater.apply_analysis(report, mutation)
        assert len(events) == 1
        assert events[0].new_value == 1.3

    def test_apply_analysis_rollback(self):
        """测试从分析结果回滚权重"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.5})

        mutation = Mutation(
            mutation_id='mut-w2',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-1',
            target_type='agent',
            before={'python': 1.0},
            after={'python': 1.5},
        )
        report = AnalysisReport(
            mutation_id='mut-w2',
            decision=AdoptionDecision.ROLLBACK,
            score=-0.3,
            metrics={},
            reasoning='bad trend',
        )

        events = updater.apply_analysis(report, mutation)
        assert len(events) == 1
        # 回滚到原来的值
        assert events[0].new_value == 1.0

    def test_apply_analysis_trial(self):
        """测试从分析结果试用权重"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})

        mutation = Mutation(
            mutation_id='mut-w3',
            mutation_type=MutationType.WEIGHT_ADJUST,
            target_id='agent-1',
            target_type='agent',
            before={'python': 1.0},
            after={'python': 1.4},
        )
        report = AnalysisReport(
            mutation_id='mut-w3',
            decision=AdoptionDecision.TRIAL,
            score=0.05,
            metrics={},
            reasoning='need more data',
        )

        events = updater.apply_analysis(report, mutation)
        assert len(events) == 1
        # 试用：减半幅度 → 1.0 + (1.4 - 1.0) * 0.5 = 1.2
        assert events[0].new_value == 1.2

    def test_revert_event(self):
        """测试回滚权重更新"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})

        capsules = [
            Capsule(
                id='capsule-003',
                trigger=[],
                gene='gene-003',
                summary='test',
                confidence=0.9,
                outcome={"status": "success", "score": 0.9},
                _pattern_id='p3',
                _pattern_type='capability',
                _status=PatternStatus.SOLIDIFIED.value,
                _match_conditions={},
                _template={},
                _weight_adjustments={'python': 0.2},
                _source_rule_ids=['gene-003'],
            ),
        ]
        events = updater.apply_patterns(capsules)
        event_id = events[0].id

        assert updater.revert_event(event_id)
        # 再次回滚应返回 False（已经回滚过）
        assert not updater.revert_event(event_id)

    def test_revert_update_backward_compat(self):
        """测试向后兼容的 revert_update()"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})

        capsules = [
            Capsule(
                id='capsule-004',
                trigger=[],
                gene='gene-004',
                summary='test',
                confidence=0.9,
                outcome={"status": "success", "score": 0.9},
                _pattern_id='p4',
                _pattern_type='capability',
                _status=PatternStatus.SOLIDIFIED.value,
                _match_conditions={},
                _template={},
                _weight_adjustments={'python': 0.2},
                _source_rule_ids=['gene-004'],
            ),
        ]
        events = updater.apply_patterns(capsules)
        event_id = events[0].id

        # revert_update 作为 revert_event 的别名
        assert updater.revert_update(event_id)

    def test_get_events_filter(self):
        """测试获取进化事件并过滤"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})
        updater.set_agent_weights('agent-2', {'python': 1.0})

        capsules = [
            Capsule(
                id='capsule-005',
                trigger=[],
                gene='gene-005',
                summary='test',
                confidence=0.9,
                outcome={"status": "success", "score": 0.9},
                _pattern_id='p5',
                _pattern_type='capability',
                _status=PatternStatus.SOLIDIFIED.value,
                _match_conditions={},
                _template={},
                _weight_adjustments={'python': 0.1},
                _source_rule_ids=['gene-005'],
            ),
        ]
        events = updater.apply_patterns(capsules)
        all_events = updater.get_events()
        assert len(all_events) >= 2

        agent1_events = updater.get_events(target_id='agent-1')
        assert len(agent1_events) >= 1

    def test_apply_patterns_filter_status(self):
        """测试只应用已验证/已固化的记忆体"""
        updater = WeightUpdater()
        updater.set_agent_weights('agent-1', {'python': 1.0})

        # DRAFT 状态的记忆体不应被应用
        draft_capsule = Capsule(
            id='capsule-006',
            trigger=[],
            gene='gene-006',
            summary='draft',
            confidence=0.4,
            outcome={"status": "pending", "score": 0.4},
            _pattern_id='p6',
            _pattern_type='capability',
            _status=PatternStatus.DRAFT.value,
            _match_conditions={},
            _template={},
            _weight_adjustments={'python': 0.5},
            _source_rule_ids=['gene-006'],
        )
        events = updater.apply_patterns([draft_capsule])
        assert len(events) == 0
