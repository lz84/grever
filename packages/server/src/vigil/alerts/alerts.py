"""
Vigil - 告警引擎 (Alerts)

异常行为检测与阈值告警。

告警规则：
- 连续失败告警
- 响应时间异常
- 信任分数骤降
- 负载异常
- 心跳超时
- 权限违规
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from vigil.common.audit import AuditAction, AuditLogger

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """告警规则定义"""
    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    # 检测函数: 返回 (triggered: bool, context: dict)
    check_fn: Callable[..., tuple]
    # 冷却时间（秒），防止告警风暴
    cooldown_seconds: int = 300
    # 是否启用
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警实例"""
    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    context: Dict[str, Any]
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None

    def acknowledge(self, by: str) -> None:
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = by

    def resolve(self, by: str) -> None:
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.resolved_by = by


class AlertChannel(Protocol):
    """告警通知通道"""

    def send(self, alert: Alert) -> None:
        ...


class LoggingAlertChannel:
    """日志告警通道 (默认)"""

    def send(self, alert: Alert) -> None:
        log_fn = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.info)
        log_fn(
            "[ALERT] %s [%s] %s - %s",
            alert.rule_name, alert.severity.value, alert.status.value, alert.message,
        )


class AlertEngine:
    """
    告警引擎

    用法：
        engine = AlertEngine(audit_logger=audit_logger)
        engine.add_rule(rule)
        engine.add_channel(channel)
        engine.check_all(context_data)
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._channels: List[AlertChannel] = [LoggingAlertChannel()]
        self._audit = audit_logger
        self._cooldowns: Dict[str, datetime] = {}  # rule_id -> last_fired_at
        self._alert_counter = 0

        # 注册内置规则
        self._register_builtin_rules()

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self._rules[rule.rule_id] = rule
        logger.info("Alert rule added: %s (%s)", rule.name, rule.rule_id)

    def add_channel(self, channel: AlertChannel) -> None:
        """添加告警通知通道"""
        self._channels.append(channel)

    def check_all(self, context: Dict[str, Any]) -> List[Alert]:
        """检查所有规则，返回触发的告警列表"""
        triggered = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if self._is_in_cooldown(rule.rule_id, rule.cooldown_seconds):
                continue

            try:
                fired, alert_context = rule.check_fn(context)
                if fired:
                    alert = self._fire_alert(rule, alert_context)
                    triggered.append(alert)
                    self._cooldowns[rule.rule_id] = datetime.now()
            except Exception as e:
                logger.error("Alert rule %s check failed: %s", rule.rule_id, e)

        return triggered

    def get_active_alerts(self, status: Optional[AlertStatus] = None) -> List[Alert]:
        """获取活跃告警"""
        alerts = [a for a in self._alerts if a.status != AlertStatus.RESOLVED]
        if status:
            alerts = [a for a in alerts if a.status == status]
        return alerts

    def acknowledge_alert(self, alert_id: str, by: str) -> Optional[Alert]:
        """确认告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id and alert.status == AlertStatus.FIRING:
                alert.acknowledge(by)
                logger.info("Alert %s acknowledged by %s", alert_id, by)
                return alert
        return None

    def resolve_alert(self, alert_id: str, by: str) -> Optional[Alert]:
        """解决告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id and alert.status != AlertStatus.RESOLVED:
                alert.resolve(by)
                if self._audit:
                    self._audit.log(
                        AuditAction.ALERT_RESOLVE, by, alert_id, "alert",
                        details={"rule_name": alert.rule_name},
                    )
                logger.info("Alert %s resolved by %s", alert_id, by)
                return alert
        return None

    # ---------- 内置规则 ----------

    def _register_builtin_rules(self) -> None:
        """注册内置告警规则"""

        # 规则 1: 连续失败
        self.add_rule(AlertRule(
            rule_id="consecutive_failures",
            name="连续失败检测",
            description="Agent 连续失败超过阈值",
            severity=AlertSeverity.WARNING,
            cooldown_seconds=600,
            check_fn=self._check_consecutive_failures,
            metadata={"threshold": 3},
        ))

        # 规则 2: 信任分数骤降
        self.add_rule(AlertRule(
            rule_id="trust_drop",
            name="信任分数骤降",
            description="Agent 信任分数下降超过阈值",
            severity=AlertSeverity.CRITICAL,
            cooldown_seconds=1800,
            check_fn=self._check_trust_drop,
            metadata={"threshold": 0.2},
        ))

        # 规则 3: 响应时间异常
        self.add_rule(AlertRule(
            rule_id="slow_response",
            name="响应时间异常",
            description="Agent 平均响应时间超过阈值",
            severity=AlertSeverity.WARNING,
            cooldown_seconds=900,
            check_fn=self._check_slow_response,
            metadata={"threshold_ms": 15000},
        ))

        # 规则 4: 心跳超时
        self.add_rule(AlertRule(
            rule_id="heartbeat_timeout",
            name="心跳超时",
            description="Agent 心跳超过指定时间未更新",
            severity=AlertSeverity.CRITICAL,
            cooldown_seconds=300,
            check_fn=self._check_heartbeat_timeout,
            metadata={"timeout_seconds": 120},
        ))

        # 规则 5: 负载过高
        self.add_rule(AlertRule(
            rule_id="high_load",
            name="负载过高",
            description="Agent 负载超过阈值",
            severity=AlertSeverity.WARNING,
            cooldown_seconds=600,
            check_fn=self._check_high_load,
            metadata={"threshold": 90},
        ))

    def _is_in_cooldown(self, rule_id: str, cooldown_seconds: int) -> bool:
        last = self._cooldowns.get(rule_id)
        if not last:
            return False
        return (datetime.now() - last).total_seconds() < cooldown_seconds

    def _fire_alert(self, rule: AlertRule, context: Dict[str, Any]) -> Alert:
        import uuid
        self._alert_counter += 1
        alert = Alert(
            alert_id=f"alert-{self._alert_counter:06d}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=context.get("message", f"Rule '{rule.name}' triggered"),
            context=context,
            triggered_at=datetime.now(),
        )
        self._alerts.append(alert)

        if self._audit:
            self._audit.log(
                AuditAction.ALERT_TRIGGER, "vigil", alert.alert_id, "alert",
                details={
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "severity": rule.severity.value,
                    "message": alert.message,
                },
                severity=rule.severity.value,
            )

        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception as e:
                logger.error("Failed to send alert via channel: %s", e)

        logger.warning(
            "Alert fired: %s [%s] - %s",
            rule.name, rule.severity.value, alert.message,
        )
        return alert

    # ---------- 内置检测函数 ----------

    @staticmethod
    def _check_consecutive_failures(context: Dict[str, Any]) -> tuple:
        threshold = 3
        agent_states = context.get("agent_states", {})
        for agent_id, state in agent_states.items():
            cf = state.get("consecutive_failures", 0)
            if cf >= threshold:
                return True, {
                    "message": f"Agent {agent_id} has {cf} consecutive failures (threshold: {threshold})",
                    "agent_id": agent_id,
                    "consecutive_failures": cf,
                    "threshold": threshold,
                }
        return False, {}

    @staticmethod
    def _check_trust_drop(context: Dict[str, Any]) -> tuple:
        threshold = 0.2
        trust_history = context.get("trust_history", {})
        for agent_id, history in trust_history.items():
            if len(history) < 2:
                continue
            old_score = history[-2]
            new_score = history[-1]
            drop = old_score - new_score
            if drop >= threshold:
                return True, {
                    "message": f"Agent {agent_id} trust dropped by {drop:.2f} ({old_score:.2f} -> {new_score:.2f})",
                    "agent_id": agent_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "drop": drop,
                    "threshold": threshold,
                }
        return False, {}

    @staticmethod
    def _check_slow_response(context: Dict[str, Any]) -> tuple:
        threshold_ms = 15000
        agent_states = context.get("agent_states", {})
        for agent_id, state in agent_states.items():
            avg_ms = state.get("avg_response_time_ms", 0)
            if avg_ms > threshold_ms:
                return True, {
                    "message": f"Agent {agent_id} avg response time {avg_ms:.0f}ms > {threshold_ms}ms",
                    "agent_id": agent_id,
                    "avg_response_time_ms": avg_ms,
                    "threshold_ms": threshold_ms,
                }
        return False, {}

    @staticmethod
    def _check_heartbeat_timeout(context: Dict[str, Any]) -> tuple:
        timeout_seconds = 120
        now = context.get("now", datetime.now())
        agent_states = context.get("agent_states", {})
        for agent_id, state in agent_states.items():
            last_hb = state.get("last_heartbeat")
            if last_hb is None:
                continue
            if isinstance(last_hb, str):
                last_hb = datetime.fromisoformat(last_hb)
            gap = (now - last_hb).total_seconds()
            if gap > timeout_seconds and state.get("status") == "online":
                return True, {
                    "message": f"Agent {agent_id} heartbeat timeout: {gap:.0f}s > {timeout_seconds}s",
                    "agent_id": agent_id,
                    "gap_seconds": gap,
                    "timeout_seconds": timeout_seconds,
                }
        return False, {}

    @staticmethod
    def _check_high_load(context: Dict[str, Any]) -> tuple:
        threshold = 90
        agent_states = context.get("agent_states", {})
        for agent_id, state in agent_states.items():
            load = state.get("load", 0)
            if load > threshold:
                return True, {
                    "message": f"Agent {agent_id} load {load}% > {threshold}%",
                    "agent_id": agent_id,
                    "load": load,
                    "threshold": threshold,
                }
        return False, {}
