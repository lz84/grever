"""
Evo - Agent-to-Agent 通信协议 (A2A)

支持 Agent 间协作和信息交换。

通信模型：
- 直接消息：点对点通信
- 广播：一对多通知
- 请求-响应：同步问答
- 协作会话：多 Agent 协作

消息类型：
- QUERY: 查询请求
- RESPONSE: 查询响应
- REQUEST: 协作请求
- OFFER: 能力提供
- NOTIFY: 通知
- ACK: 确认
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """消息类型"""
    QUERY = "query"
    RESPONSE = "response"
    REQUEST = "request"
    OFFER = "offer"
    NOTIFY = "notify"
    ACK = "ack"
    ERROR = "error"


class MessagePriority(str, Enum):
    """消息优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class A2AMessage:
    """A2A 通信消息"""
    message_id: str
    message_type: MessageType
    priority: MessagePriority
    status: MessageStatus
    sender_id: str
    receiver_id: str  # "*" 表示广播
    # 内容
    subject: str
    body: Dict[str, Any]
    # 元数据
    correlation_id: Optional[str] = None  # 关联请求/响应
    in_reply_to: Optional[str] = None    # 回复的消息 ID
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "subject": self.subject,
            "body": self.body,
            "correlation_id": self.correlation_id,
            "in_reply_to": self.in_reply_to,
            "tags": self.tags,
        }


@dataclass
class CollaborationSession:
    """协作会话"""
    session_id: str
    initiator_id: str
    participants: Set[str]
    topic: str
    status: str  # "active" | "completed" | "cancelled"
    messages: List[A2AMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "initiator_id": self.initiator_id,
            "participants": list(self.participants),
            "topic": self.topic,
            "status": self.status,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
        }


class A2AProtocol:
    """
    Agent-to-Agent 通信协议

    用法：
        protocol = A2AProtocol()
        protocol.register_handler("query", my_handler)
        msg = protocol.send(sender_id, receiver_id, "query", body)
    """

    # 消息 TTL（默认 5 分钟）
    DEFAULT_TTL_SECONDS = 300

    def __init__(self):
        # 消息存储
        self._messages: Dict[str, A2AMessage] = {}
        # 消息队列（按 receiver_id 分组）
        self._inboxes: Dict[str, List[A2AMessage]] = {}
        # 广播消息
        self._broadcasts: List[A2AMessage] = []
        # 消息处理器: message_type -> handler_fn
        self._handlers: Dict[MessageType, Callable] = {}
        # 协作会话
        self._sessions: Dict[str, CollaborationSession] = {}
        # Agent 能力注册: agent_id -> capabilities
        self._agent_capabilities: Dict[str, List[str]] = {}
        self._message_counter = 0

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """注册消息处理器"""
        self._handlers[message_type] = handler
        logger.info("Handler registered for %s", message_type.value)

    def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """注册 Agent 能力"""
        self._agent_capabilities[agent_id] = capabilities
        self._inboxes.setdefault(agent_id, [])
        logger.info("Agent %s registered with capabilities: %s", agent_id, capabilities)

    # ---------- 消息发送 ----------

    def send(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: MessageType,
        subject: str = "",
        body: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        tags: Optional[List[str]] = None,
    ) -> A2AMessage:
        """发送消息"""
        self._message_counter += 1
        msg = A2AMessage(
            message_id=f"a2a-{self._message_counter:06d}",
            message_type=message_type,
            priority=priority,
            status=MessageStatus.PENDING,
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=subject,
            body=body or {},
            correlation_id=correlation_id,
            in_reply_to=in_reply_to,
            expires_at=datetime.now() + timedelta(seconds=ttl_seconds),
            tags=tags or [],
        )

        self._messages[msg.message_id] = msg

        if receiver_id == "*":
            # 广播
            self._broadcasts.append(msg)
            msg.status = MessageStatus.SENT
            logger.info("Broadcast from %s: %s", sender_id, subject)
        else:
            # 点对点
            inbox = self._inboxes.setdefault(receiver_id, [])
            inbox.append(msg)
            msg.status = MessageStatus.SENT
            logger.debug("Message %s from %s to %s: %s", msg.message_id, sender_id, receiver_id, subject)

        return msg

    def send_query(
        self,
        sender_id: str,
        receiver_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> A2AMessage:
        """发送查询"""
        return self.send(
            sender_id, receiver_id, MessageType.QUERY,
            subject=question,
            body={"question": question, "context": context or {}},
            **kwargs,
        )

    def send_response(
        self,
        sender_id: str,
        receiver_id: str,
        original_message_id: str,
        answer: Dict[str, Any],
        **kwargs,
    ) -> A2AMessage:
        """发送响应"""
        return self.send(
            sender_id, receiver_id, MessageType.RESPONSE,
            subject="Response",
            body={"answer": answer},
            in_reply_to=original_message_id,
            **kwargs,
        )

    def send_request(
        self,
        sender_id: str,
        receiver_id: str,
        task_description: str,
        requirements: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> A2AMessage:
        """发送协作请求"""
        return self.send(
            sender_id, receiver_id, MessageType.REQUEST,
            subject=task_description,
            body={"task": task_description, "requirements": requirements or {}},
            **kwargs,
        )

    def send_offer(
        self,
        sender_id: str,
        receiver_id: str,
        capabilities: List[str],
        availability: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> A2AMessage:
        """发送能力提供"""
        return self.send(
            sender_id, receiver_id, MessageType.OFFER,
            subject=f"Capabilities: {capabilities}",
            body={"capabilities": capabilities, "availability": availability or {}},
            **kwargs,
        )

    def send_notify(
        self,
        sender_id: str,
        receiver_id: str,
        notification: str,
        data: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.LOW,
        **kwargs,
    ) -> A2AMessage:
        """发送通知"""
        return self.send(
            sender_id, receiver_id, MessageType.NOTIFY,
            subject=notification,
            body={"notification": notification, "data": data or {}},
            priority=priority,
            **kwargs,
        )

    # ---------- 消息接收 ----------

    def receive(self, agent_id: str, limit: int = 50) -> List[A2AMessage]:
        """接收消息"""
        inbox = self._inboxes.get(agent_id, [])

        # 清理过期消息
        now = datetime.now()
        valid = []
        expired = []
        for msg in inbox:
            if msg.expires_at and msg.expires_at < now:
                msg.status = MessageStatus.EXPIRED
                expired.append(msg)
            else:
                msg.status = MessageStatus.DELIVERED
                msg.delivered_at = now
                valid.append(msg)

        # 移除过期消息
        for msg in expired:
            inbox.remove(msg)

        # 取最新消息
        result = valid[-limit:] if len(valid) > limit else valid

        # 处理
        for msg in result:
            self._process_message(msg)

        return result

    def receive_broadcast(self, agent_id: str) -> List[A2AMessage]:
        """接收广播消息"""
        now = datetime.now()
        relevant = []
        for msg in self._broadcasts:
            if msg.expires_at and msg.expires_at < now:
                continue
            if msg.sender_id != agent_id:  # 不接收自己的广播
                msg.status = MessageStatus.DELIVERED
                msg.delivered_at = now
                relevant.append(msg)
                self._process_message(msg)
        return relevant

    def acknowledge(self, message_id: str) -> bool:
        """确认收到消息"""
        msg = self._messages.get(message_id)
        if msg:
            msg.status = MessageStatus.ACKNOWLEDGED
            msg.acknowledged_at = datetime.now()
            logger.debug("Message %s acknowledged", message_id)
            return True
        return False

    # ---------- 协作会话 ----------

    def create_session(
        self,
        initiator_id: str,
        participants: List[str],
        topic: str,
    ) -> CollaborationSession:
        """创建协作会话"""
        session = CollaborationSession(
            session_id=f"session-{uuid.uuid4().hex[:8]}",
            initiator_id=initiator_id,
            participants={initiator_id} | set(participants),
            topic=topic,
            status="active",
        )
        self._sessions[session.session_id] = session
        logger.info("Session %s created: %s (%d participants)", session.session_id, topic, len(session.participants))

        # 通知所有参与者
        for pid in participants:
            self.send_notify(
                initiator_id, pid,
                f"Invited to collaboration: {topic}",
                data={"session_id": session.session_id},
                priority=MessagePriority.HIGH,
            )

        return session

    def add_session_message(self, session_id: str, message: A2AMessage) -> bool:
        """添加会话消息"""
        session = self._sessions.get(session_id)
        if session and session.status == "active":
            session.messages.append(message)
            return True
        return False

    def close_session(self, session_id: str, result: Optional[Dict[str, Any]] = None) -> Optional[CollaborationSession]:
        """关闭协作会话"""
        session = self._sessions.get(session_id)
        if session:
            session.status = "completed"
            session.completed_at = datetime.now()
            session.result = result
            logger.info("Session %s completed", session_id)
            return session
        return None

    # ---------- 查询 ----------

    def find_agents_by_capability(self, capability: str) -> List[str]:
        """查找具有指定能力的 Agent"""
        return [
            agent_id for agent_id, caps in self._agent_capabilities.items()
            if capability in caps
        ]

    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        return self._agent_capabilities.get(agent_id, [])

    def get_message(self, message_id: str) -> Optional[A2AMessage]:
        return self._messages.get(message_id)

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        return self._sessions.get(session_id)

    def list_active_sessions(self) -> List[CollaborationSession]:
        return [s for s in self._sessions.values() if s.status == "active"]

    # ---------- 内部方法 ----------

    def _process_message(self, msg: A2AMessage) -> None:
        """处理收到的消息"""
        handler = self._handlers.get(msg.message_type)
        if handler:
            try:
                handler(msg)
            except Exception as e:
                logger.error("Handler error for %s: %s", msg.message_type, e)
                # 发送错误响应
                if msg.sender_id:
                    self.send(
                        msg.receiver_id, msg.sender_id, MessageType.ERROR,
                        subject=f"Error processing {msg.message_type.value}",
                        body={"error": str(e), "original_message_id": msg.message_id},
                        in_reply_to=msg.message_id,
                    )
