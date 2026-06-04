# -*- coding: utf-8 -*-
"""
单元测试: reins/vigil/ 模块

覆盖:
1. TrustEvaluator - 信任评分计算
2. AuditLogger - 审计日志
3. AlertEngine - 告警引擎
4. AccessController - RBAC 访问控制
"""

import pytest
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from vigil.trust import TrustEvaluator, TrustLevel, TrustMetrics, TrustScore
from vigil.common.audit import AuditLogger, AuditAction
from vigil.alerts.alerts import (
    AlertEngine, AlertRule, Alert, AlertSeverity, AlertStatus, LoggingAlertChannel
)
from vigil.access.access import (
    AccessController, UserContext, Role, Permission,
    require_role, require_permission
)


# ============================================================================
# TrustEvaluator Tests
# ============================================================================

class TestTrustEvaluator:
    """信任评估器测试"""

    def _make_records(self, n_success=5, n_failed=1, n_timeout=0, now=None):
        """生成测试历史记录"""
        now = now or datetime.now()
        records = []
        for i in range(n_success):
            records.append({
                'status': 'success',
                'quality_score': 0.8 + i * 0.02,
                'duration_ms': 1000 + i * 100,
                'created_at': now - timedelta(days=n_success - i),
            })
        for i in range(n_failed):
            records.append({
                'status': 'failed',
                'quality_score': 0.2,
                'duration_ms': 5000,
                'created_at': now - timedelta(hours=1),
            })
        for i in range(n_timeout):
            records.append({
                'status': 'timeout',
                'quality_score': None,
                'duration_ms': 30000,
                'created_at': now - timedelta(hours=2),
            })
        return records

    def test_evaluate_high_trust(self):
        """测试高信任度 Agent"""
        evaluator = TrustEvaluator()
        records = self._make_records(n_success=20, n_failed=1)
        score = evaluator.evaluate('agent-good', records)
        assert score.score > 0.5
        assert score.level in (TrustLevel.TRUSTED, TrustLevel.HIGHLY_TRUSTED, TrustLevel.MODERATE)

    def test_evaluate_low_trust(self):
        """测试低信任度 Agent"""
        evaluator = TrustEvaluator()
        records = self._make_records(n_success=1, n_failed=10)
        score = evaluator.evaluate('agent-bad', records)
        # 低信任度 Agent 分数应显著低于高信任度
        assert score.score < 0.65
        assert score.level in (TrustLevel.MODERATE, TrustLevel.LOW, TrustLevel.UNTRUSTED)

    def test_evaluate_no_records(self):
        """测试无记录时的默认评估"""
        evaluator = TrustEvaluator()
        score = evaluator.evaluate('agent-new', [])
        # longevity=0.0 拉低了总分: 0.5*0.35 + 0.5*0.20 + 0.5*0.20 + 0.5*0.15 + 0.0*0.10 = 0.45
        assert score.score == 0.45
        assert score.level == TrustLevel.MODERATE

    def test_evaluate_with_config(self):
        """测试自定义权重配置"""
        config = {
            'weight_success_rate': 0.5,
            'weight_consistency': 0.1,
            'weight_timeliness': 0.1,
            'weight_quality': 0.2,
            'weight_longevity': 0.1,
        }
        evaluator = TrustEvaluator(config=config)
        records = self._make_records(n_success=10)
        score = evaluator.evaluate('agent-custom', records)
        assert score.score > 0

    def test_consecutive_failure_penalty(self):
        """测试连续失败惩罚"""
        evaluator = TrustEvaluator()
        records = []
        now = datetime.now()
        for i in range(3):
            records.append({
                'status': 'failed',
                'quality_score': 0.1,
                'created_at': now - timedelta(hours=i),
            })
        score = evaluator.evaluate('agent-failing', records)
        assert score.metrics.consecutive_failures == 3

    def test_cache(self):
        """测试信任评分缓存"""
        evaluator = TrustEvaluator()
        records = self._make_records(n_success=5)
        score = evaluator.evaluate('agent-1', records)

        cached = evaluator.get_cached('agent-1')
        assert cached is not None
        assert cached.agent_id == 'agent-1'

        # 不存在的缓存
        assert evaluator.get_cached('nonexistent') is None

        # 清除缓存
        evaluator.clear_cache('agent-1')
        assert evaluator.get_cached('agent-1') is None

        # 全部清除
        evaluator.evaluate('agent-2', records)
        evaluator.clear_cache()
        assert evaluator.get_cached('agent-2') is None

    def test_trust_levels(self):
        """测试信任等级分类"""
        evaluator = TrustEvaluator()
        # 验证等级映射
        assert evaluator._classify_level(0.9) == TrustLevel.HIGHLY_TRUSTED
        assert evaluator._classify_level(0.7) == TrustLevel.TRUSTED
        assert evaluator._classify_level(0.5) == TrustLevel.MODERATE
        assert evaluator._classify_level(0.3) == TrustLevel.LOW
        assert evaluator._classify_level(0.1) == TrustLevel.UNTRUSTED

    def test_confidence_calculation(self):
        """测试置信度计算"""
        evaluator = TrustEvaluator()
        # 少样本低置信度
        assert evaluator._compute_confidence(0) < 0.5
        assert evaluator._compute_confidence(3) < 0.5
        # 多样本高置信度
        assert evaluator._compute_confidence(50) == 1.0
        # 中等样本
        mid_conf = evaluator._compute_confidence(25)
        assert 0.5 < mid_conf < 1.0

    def test_timeliness_computation(self):
        """测试及时性计算"""
        metrics = TrustMetrics(agent_id='test', avg_response_time_ms=500)
        assert TrustEvaluator._compute_timeliness(metrics) == 1.0

        metrics = TrustMetrics(agent_id='test', avg_response_time_ms=30000)
        assert TrustEvaluator._compute_timeliness(metrics) == 0.0

        metrics = TrustMetrics(agent_id='test', avg_response_time_ms=0)
        assert TrustEvaluator._compute_timeliness(metrics) == 0.5

    def test_consistency_computation(self):
        """测试一致性计算"""
        # 全成功 → 0 transitions → 一致性最高 (1.0)
        records = [{'status': 'success'}] * 10
        assert TrustEvaluator._compute_consistency(records, datetime.now()) == 1.0

        # 频繁交替 → 低一致性
        records = []
        for i in range(10):
            records.append({'status': 'success' if i % 2 == 0 else 'failed'})
        consistency = TrustEvaluator._compute_consistency(records, datetime.now())
        assert consistency < 0.5


# ============================================================================
# AuditLogger Tests
# ============================================================================

class TestAuditLogger:
    """审计日志记录器测试"""

    def test_log_entry(self):
        """测试记录审计日志"""
        sink = MemoryAuditSink()
        logger = AuditLogger(sink=sink)
        entry = logger.log(
            action=AuditAction.TASK_ASSIGN,
            actor_id='scheduler',
            target_id='task-123',
            target_type='task',
            details={'agent_id': 'agent-456'},
        )
        assert entry.action == AuditAction.TASK_ASSIGN
        assert entry.actor_id == 'scheduler'
        assert entry.target_id == 'task-123'

    def test_query_audit(self):
        """测试查询审计日志"""
        sink = MemoryAuditSink()
        logger = AuditLogger(sink=sink)
        logger.log(AuditAction.TASK_ASSIGN, 'scheduler', 'task-1', 'task')
        logger.log(AuditAction.TASK_COMPLETE, 'agent-1', 'task-1', 'task')
        logger.log(AuditAction.TASK_ASSIGN, 'scheduler', 'task-2', 'task')

        # 按操作类型查询
        assign_logs = logger.query(action=AuditAction.TASK_ASSIGN)
        assert len(assign_logs) == 2

        # 按执行者查询
        scheduler_logs = logger.query(actor_id='scheduler')
        assert len(scheduler_logs) == 2

    def test_convenience_methods(self):
        """测试便捷方法"""
        sink = MemoryAuditSink()
        logger = AuditLogger(sink=sink)

        entry = logger.log_agent_register('agent-001')
        assert entry.action == AuditAction.AGENT_REGISTER

        entry = logger.log_task_assign('task-001', 'agent-001')
        assert entry.action == AuditAction.TASK_ASSIGN
        assert entry.details['assigned_to'] == 'agent-001'

        entry = logger.log_task_complete('task-001', 'agent-001')
        assert entry.action == AuditAction.TASK_COMPLETE

        entry = logger.log_task_fail('task-001', 'agent-001', error='timeout')
        assert entry.action == AuditAction.TASK_FAIL
        assert entry.severity == 'error'

        entry = logger.log_trust_change('agent-001', 0.5, 0.8)
        assert entry.action == AuditAction.TRUST_CHANGE

    def test_audit_entry_serialization(self):
        """测试审计条目序列化"""
        entry = AuditEntry(
            id='test-id',
            timestamp=datetime.now(),
            action=AuditAction.TASK_CREATE,
            actor_id='user-1',
            target_id='task-1',
            details={'key': 'value'},
        )
        d = entry.to_dict()
        assert 'timestamp' in d
        assert d['action'] == 'task.create'

        json_str = entry.to_json()
        assert 'task.create' in json_str

    def test_memory_sink_max_entries(self):
        """测试内存存储的最大条目限制"""
        sink = MemoryAuditSink(max_entries=5)
        for i in range(10):
            sink.write(AuditEntry(
                id=str(i),
                timestamp=datetime.now(),
                action=AuditAction.TASK_CREATE,
                actor_id='system',
            ))
        assert len(sink._entries) == 5

    def test_memory_sink_query_filters(self):
        """测试内存存储的查询过滤"""
        sink = MemoryAuditSink()
        now = datetime.now()
        sink.write(AuditEntry(id='1', timestamp=now, action=AuditAction.TASK_CREATE, actor_id='a1'))
        sink.write(AuditEntry(id='2', timestamp=now, action=AuditAction.TASK_ASSIGN, actor_id='a2', severity='warning'))

        results = sink.query(actor_id='a1')
        assert len(results) == 1
        assert results[0].actor_id == 'a1'

        results = sink.query(severity='warning')
        assert len(results) == 1


# ============================================================================
# AlertEngine Tests
# ============================================================================

class TestAlertEngine:
    """告警引擎测试"""

    def test_builtin_rules(self):
        """测试内置规则注册"""
        engine = AlertEngine()
        # 应该有 5 个内置规则
        assert len(engine._rules) == 5
        assert 'consecutive_failures' in engine._rules
        assert 'trust_drop' in engine._rules
        assert 'slow_response' in engine._rules
        assert 'heartbeat_timeout' in engine._rules
        assert 'high_load' in engine._rules

    def test_fire_consecutive_failures_alert(self):
        """测试连续失败告警触发"""
        engine = AlertEngine()
        context = {
            'agent_states': {
                'agent-1': {'consecutive_failures': 5, 'status': 'online'},
            }
        }
        alerts = engine.check_all(context)
        assert len(alerts) >= 1
        assert any(a.rule_id == 'consecutive_failures' for a in alerts)

    def test_fire_trust_drop_alert(self):
        """测试信任分数骤降告警"""
        engine = AlertEngine()
        context = {
            'trust_history': {
                'agent-1': [0.9, 0.5],  # 下降 0.4 > 阈值 0.2
            }
        }
        alerts = engine.check_all(context)
        assert len(alerts) >= 1
        assert any(a.rule_id == 'trust_drop' for a in alerts)

    def test_fire_slow_response_alert(self):
        """测试慢响应告警"""
        engine = AlertEngine()
        context = {
            'agent_states': {
                'agent-1': {'avg_response_time_ms': 20000},
            }
        }
        alerts = engine.check_all(context)
        assert any(a.rule_id == 'slow_response' for a in alerts)

    def test_alert_lifecycle(self):
        """测试告警生命周期（触发→确认→解决）"""
        engine = AlertEngine()
        context = {
            'agent_states': {
                'agent-1': {'consecutive_failures': 5},
            }
        }
        alerts = engine.check_all(context)
        alert = alerts[0]

        # 确认
        acknowledged = engine.acknowledge_alert(alert.alert_id, 'admin')
        assert acknowledged is not None
        assert acknowledged.status == AlertStatus.ACKNOWLEDGED

        # 解决
        resolved = engine.resolve_alert(alert.alert_id, 'admin')
        assert resolved is not None
        assert resolved.status == AlertStatus.RESOLVED

    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        engine = AlertEngine()
        # 添加一个自定义规则来确保至少两个告警
        engine.add_rule(AlertRule(
            rule_id='custom_high_load',
            name='负载检测',
            description='测试用',
            severity=AlertSeverity.WARNING,
            cooldown_seconds=0,  # 无冷却
            check_fn=lambda ctx: (
                any(s.get('load', 0) > 50 for s in ctx.get('agent_states', {}).values()),
                {'message': 'high load detected'},
            ),
        ))
        context = {
            'agent_states': {
                'agent-1': {'consecutive_failures': 5},
                'agent-2': {'load': 95},
            }
        }
        engine.check_all(context)
        active = engine.get_active_alerts()
        assert len(active) >= 2

        # 解决后不应出现在活跃列表中
        engine.resolve_alert(active[0].alert_id, 'admin')
        active = engine.get_active_alerts()

    def test_custom_rule(self):
        """测试添加自定义规则"""
        engine = AlertEngine()
        custom_rule = AlertRule(
            rule_id='custom_rule',
            name='自定义规则',
            description='测试用',
            severity=AlertSeverity.INFO,
            check_fn=lambda ctx: (True, {'message': 'custom fired'}),
        )
        engine.add_rule(custom_rule)
        assert 'custom_rule' in engine._rules

    def test_add_channel(self):
        """测试添加告警通道"""
        engine = AlertEngine()
        initial_channels = len(engine._channels)
        mock_channel = MagicMock()
        engine.add_channel(mock_channel)
        assert len(engine._channels) == initial_channels + 1

    def test_no_alert_when_conditions_not_met(self):
        """测试条件不满足时不触发告警"""
        engine = AlertEngine()
        context = {
            'agent_states': {
                'agent-1': {'consecutive_failures': 0, 'status': 'online'},
            },
            'trust_history': {},
        }
        alerts = engine.check_all(context)
        # 应该没有告警
        consecutive_alerts = [a for a in alerts if a.rule_id == 'consecutive_failures']
        assert len(consecutive_alerts) == 0


# ============================================================================
# AccessController Tests
# ============================================================================

class TestAccessController:
    """RBAC 访问控制器测试"""

    def test_role_permissions(self):
        """测试角色权限映射"""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.CONFIG_ADMIN in admin_perms
        assert len(admin_perms) == len(Permission)  # admin 有所有权限

        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.TASK_READ in viewer_perms
        assert Permission.TASK_WRITE not in viewer_perms

    def test_user_context_permission(self):
        """测试用户上下文权限检查"""
        ctx = UserContext(user_id='user-1', role=Role.ADMIN)
        assert ctx.has_permission(Permission.CONFIG_ADMIN)
        assert ctx.has_permission(Permission.TASK_WRITE)

        ctx = UserContext(user_id='user-2', role=Role.VIEWER)
        assert not ctx.has_permission(Permission.TASK_WRITE)
        assert ctx.has_permission(Permission.TASK_READ)

    def test_user_context_any_all_permissions(self):
        """测试权限组合检查"""
        ctx = UserContext(user_id='user-1', role=Role.OPERATOR)
        assert ctx.has_any_permission(Permission.TASK_WRITE, Permission.CONFIG_ADMIN)
        assert ctx.has_all_permissions(Permission.TASK_READ, Permission.TASK_WRITE)
        assert not ctx.has_all_permissions(Permission.TASK_READ, Permission.CONFIG_ADMIN)

    def test_access_controller_basic(self):
        """测试访问控制器基本功能"""
        ac = AccessController()
        ac.set_user_role('user-1', Role.ADMIN)
        ac.set_user_role('user-2', Role.VIEWER)

        ctx = ac.create_context('user-1')
        assert ctx is not None
        assert ctx.role == Role.ADMIN

        # 不存在的用户
        ctx = ac.create_context('nonexistent')
        assert ctx is None

    def test_check_permission(self):
        """测试权限检查"""
        ac = AccessController()
        ac.set_user_role('admin-1', Role.ADMIN)
        admin_ctx = ac.create_context('admin-1')

        assert ac.check_permission(admin_ctx, Permission.CONFIG_ADMIN)
        assert ac.check_permission(admin_ctx, Permission.TASK_WRITE)

    def test_check_resource_access(self):
        """测试资源级访问检查"""
        ac = AccessController()
        ac.set_user_role('operator-1', Role.OPERATOR)
        ctx = ac.create_context('operator-1')

        assert ac.check_resource_access(ctx, 'task', 'task-1', 'read')
        assert ac.check_resource_access(ctx, 'task', 'task-1', 'write')
        assert not ac.check_resource_access(ctx, 'config', 'config-1', 'admin')

    def test_custom_permissions(self):
        """测试自定义权限"""
        ac = AccessController()
        ac.set_user_role('analyst-1', Role.ANALYST)
        ctx = ac.create_context('analyst-1')

        # 默认分析师没有 write 权限
        assert not ac.check_permission(ctx, Permission.TASK_WRITE)

        # 添加自定义权限
        ac.add_custom_permission(Role.ANALYST, Permission.TASK_WRITE)
        assert ac.check_permission(ctx, Permission.TASK_WRITE)

        # 移除自定义权限
        ac.remove_custom_permission(Role.ANALYST, Permission.TASK_WRITE)
        assert not ac.check_permission(ctx, Permission.TASK_WRITE)

    def test_list_user_permissions(self):
        """测试列出用户权限"""
        ac = AccessController()
        ac.set_user_role('agent-1', Role.AGENT)
        perms = ac.list_user_permissions('agent-1')
        assert Permission.TASK_READ in perms
        assert Permission.TASK_EXECUTE in perms
        assert Permission.CONFIG_ADMIN not in perms

    def test_agent_mapping(self):
        """测试 Agent 到用户映射"""
        ac = AccessController()
        ac.map_agent_to_user('agent-001', 'user-001')
        assert ac.get_user_for_agent('agent-001') == 'user-001'
        assert ac.get_user_for_agent('nonexistent') is None

    def test_require_role_decorator(self):
        """测试 require_role 装饰器"""
        @require_role(Role.ADMIN)
        def admin_only(ctx: UserContext):
            return 'ok'

        admin_ctx = UserContext(user_id='admin', role=Role.ADMIN)
        assert admin_only(admin_ctx) == 'ok'

        viewer_ctx = UserContext(user_id='viewer', role=Role.VIEWER)
        with pytest.raises(PermissionError):
            admin_only(viewer_ctx)

    def test_require_permission_decorator(self):
        """测试 require_permission 装饰器"""
        @require_permission(Permission.TASK_WRITE, Permission.TASK_ASSIGN)
        def task_writer(ctx: UserContext):
            return 'ok'

        op_ctx = UserContext(user_id='operator', role=Role.OPERATOR)
        assert task_writer(op_ctx) == 'ok'

        viewer_ctx = UserContext(user_id='viewer', role=Role.VIEWER)
        with pytest.raises(PermissionError):
            task_writer(viewer_ctx)

    def test_require_role_with_kwargs(self):
        """测试装饰器通过 kwargs 获取 UserContext"""
        @require_role(Role.ADMIN)
        def admin_func(ctx: UserContext):
            return 'passed'

        admin_ctx = UserContext(user_id='admin', role=Role.ADMIN)
        result = admin_func(ctx=admin_ctx)
        assert result == 'passed'

    def test_require_role_missing_context(self):
        """测试装饰器缺少 UserContext 时抛异常"""
        @require_role(Role.ADMIN)
        def admin_func(ctx: UserContext):
            return 'should not reach'

        with pytest.raises(PermissionError):
            admin_func()
