"""DAG 对话上下文管理（内存存储）"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class DAGModification:
    """一次 DAG 修改操作"""
    action: str
    params: dict
    description: str

@dataclass
class ConversationTurn:
    """一轮对话"""
    role: str           # "user" / "agent"
    content: str        # 对话内容
    modification: Optional[DAGModification] = None
    timestamp: float = 0

@dataclass
class ConversationContext:
    """会话上下文"""
    workflow_id: str
    conversation_id: str
    history: list = field(default_factory=list)
    pending_modification: Optional[DAGModification] = None
    current_dag: Optional[dict] = None

    def add_turn(self, role: str, content: str, modification: DAGModification = None):
        self.history.append(ConversationTurn(
            role=role, content=content, modification=modification, timestamp=time.time()
        ))

    def get_history_text(self) -> str:
        """对话历史格式化为文本，供 LLM 使用"""
        if not self.history:
            return "（暂无对话历史）"
        parts = []
        for turn in self.history[-6:]:
            role_label = "用户" if turn.role == "user" else "刚子"
            parts.append(f"{role_label}：{turn.content}")
            if turn.modification:
                parts.append(f"  → 操作：{turn.modification.action} - {turn.modification.description}")
        return "\n".join(parts)

# 内存存储：workflow_id → ConversationContext
_conversation_store: dict[str, ConversationContext] = {}

def _get_or_create_context(workflow_id: str) -> ConversationContext:
    if workflow_id not in _conversation_store:
        _conversation_store[workflow_id] = ConversationContext(
            workflow_id=workflow_id,
            conversation_id=str(uuid.uuid4())[:8],
        )
    return _conversation_store[workflow_id]