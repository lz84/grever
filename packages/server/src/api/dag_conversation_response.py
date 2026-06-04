"""DAG 对话响应构建器"""

from typing import Optional

from .dag_conversation_context import ConversationContext

def _make_response(
    content: str,
    dag: dict,
    context: ConversationContext,
    suggestions: list,
    pending_action: dict = None,
    confidence: float = None,
    follow_up: str = None,
    error: str = None,
) -> dict:
    return {
        "role": "agent",
        "content": content,
        "suggestions": suggestions,
        "dag": dag,
        "pending_action": pending_action,
        "confidence": confidence,
        "follow_up": follow_up,
        "error": error,
    }