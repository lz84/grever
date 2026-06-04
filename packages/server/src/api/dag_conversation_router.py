"""DAG 对话式编辑 - API 端点（Facade 模式）

各子模块职责：
- dag_conversation_context: 会话上下文管理
- dag_conversation_intent: LLM 意图解析 + 降级正则匹配
- dag_conversation_sync: DAG → projects 同步
- dag_conversation_response: 响应构建
"""

import time
from typing import Literal

from pydantic import BaseModel
from fastapi import Body

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from reins.common.database import get_db

from .dag_conversation_context import (
    _get_or_create_context,
    ConversationContext,
    DAGModification,
)
from .dag_conversation_intent import (
    _parse_intent_with_llm,
    _generate_proactive_suggestions,
)
from .dag_conversation_sync import _sync_projects_from_dag
from .dag_conversation_response import _make_response
from reins.api.workflow_dag_logic import _get_workflow_dag, _save_dag, _validate_dag, _sync_steps, _execute_action, _find_node

router = APIRouter(prefix="/api/v1/workflows", tags=["dag-conversation"])

# ============================================================================
# 请求模型
# ============================================================================

class ConverseRequest(BaseModel):
    message: str = ""
    action: Literal["chat", "confirm", "cancel", "suggest"] = "chat"

# ============================================================================
# 辅助：操作执行
# ============================================================================

def _apply_modification(dag: dict, dag_nodes: list, mod: DAGModification) -> tuple[dict, str]:
    """
    将 DAGModification 应用到 DAG，返回 (result_dag, error)。
    """
    op = {"action": mod.action, "params": mod.params}

    if mod.action == "insert_after":
        ref_name = mod.params.get("ref_node_id", "")
        ref_node = _find_node(dag_nodes, ref_name)
        ref_id = ref_node["id"] if ref_node else ref_name
        op.update({
            "action": "insert_after",
            "ref_id": ref_id,
            "new_title": mod.params.get("new_title", "新节点"),
        })
    elif mod.action == "delete_node":
        node_name = mod.params.get("node_id", "")
        target_node = _find_node(dag_nodes, node_name)
        node_id = target_node["id"] if target_node else node_name
        op.update({
            "action": "delete",
            "node_id": node_id,
        })
    elif mod.action == "rename_node":
        node_name = mod.params.get("node_id", "")
        target_node = _find_node(dag_nodes, node_name)
        node_id = target_node["id"] if target_node else node_name
        op.update({
            "action": "rename",
            "node_id": node_id,
            "new_title": mod.params.get("new_title"),
        })

    result_dag, changes, error = _execute_action(dag, op)
    return result_dag, error or None

# ============================================================================
# API 端点
# ============================================================================

@router.post("/{workflow_id}/dag/converse")
async def dag_converse(
    workflow_id: str,
    req: ConverseRequest = Body(...),
):
    """
    对话式 DAG 编辑主入口。

    用户发送自然语言消息，Agent 理解意图后：
    - ask_clarify: 需要追问，获取更多信息
    - suggest: 提出了具体的修改建议，等待确认
    - execute: 用户确认，执行修改
    - cancel: 用户取消
    """
    db_gen = get_db()
    db = next(db_gen)

    try:
        dag_data = _get_workflow_dag(db, workflow_id)
        if not dag_data:
            raise HTTPException(404, "Workflow not found")

        dag = dag_data.get("dag", {})
        context = _get_or_create_context(workflow_id)
        context.current_dag = dag
        dag_nodes = dag.get("nodes", [])

        # --- confirm ---
        if req.action == "confirm":
            if not context.pending_modification:
                return _make_response("没有待确认的修改。", dag, context, [])
            mod = context.pending_modification
            context.add_turn("user", req.message, None)

            try:
                result_dag, error = _apply_modification(dag, dag_nodes, mod)
                if error:
                    raise Exception(error)

                _validate_dag(result_dag)
                _save_dag(db, workflow_id, result_dag)
                _sync_steps(db, workflow_id, result_dag)
                _sync_projects_from_dag(db, workflow_id, result_dag)
                db.commit()

                response_text = f"已完成修改：{mod.description}"
                context.add_turn("agent", response_text, mod)
                context.pending_modification = None
                context.current_dag = result_dag
                suggestions = await _generate_proactive_suggestions(result_dag, context)
                return _make_response(response_text, result_dag, context, suggestions)

            except Exception as e:
                db.rollback()
                return _make_response(f"执行失败：{str(e)}", dag, context, [], error=str(e))

        # --- cancel ---
        if req.action == "cancel":
            context.pending_modification = None
            context.add_turn("user", req.message, None)
            response_text = "好的，已取消本次修改。"
            context.add_turn("agent", response_text, None)
            suggestions = await _generate_proactive_suggestions(dag, context)
            return _make_response(response_text, dag, context, suggestions)

        # --- suggest: 请求主动建议 ---
        if req.action == "suggest":
            context.add_turn("user", req.message, None)
            suggestions = await _generate_proactive_suggestions(dag, context)

            if not suggestions:
                response_text = (
                    "我分析了一下当前工作流，没有发现明显的问题。"
                    "你有什么想调整的吗？"
                )
            else:
                lines = [f"{i+1}. **{s['title']}**：{s['reason']}"
                          for i, s in enumerate(suggestions)]
                response_text = (
                    f"我分析了一下当前工作流，有 {len(suggestions)} 个地方值得关注：\n\n"
                    + "\n".join(lines)
                )

            context.add_turn("agent", response_text, None)
            return _make_response(response_text, dag, context, suggestions)

        # --- chat: 正常对话 ---
        intent_result = await _parse_intent_with_llm(req.message, dag, context)
        intent_type = intent_result["intent_type"]
        response_text = intent_result["response"]

        context.add_turn("user", req.message, None)

        if intent_type in ("ask_clarify", "cancel"):
            context.add_turn("agent", response_text, None)
            suggestions = await _generate_proactive_suggestions(dag, context)
            return _make_response(
                response_text, dag, context, suggestions,
                follow_up=intent_result.get("follow_up"),
            )

        if intent_type == "suggest":
            mod = DAGModification(
                action=intent_result["action"],
                params=intent_result["params"],
                description=intent_result["description"],
            )
            context.pending_modification = mod
            context.add_turn("agent", response_text, mod)
            return _make_response(
                response_text, dag, context, [],
                pending_action={
                    "action": mod.action,
                    "params": mod.params,
                    "description": mod.description,
                },
                confidence=intent_result.get("confidence", 0.8),
            )

        if intent_type == "execute":
            if not context.pending_modification:
                context.add_turn("agent", response_text, None)
                suggestions = await _generate_proactive_suggestions(dag, context)
                return _make_response(response_text, dag, context, suggestions)

            mod = context.pending_modification
            context.add_turn("agent", response_text, mod)

            try:
                result_dag, error = _apply_modification(dag, dag_nodes, mod)
                if error:
                    raise Exception(error)

                _validate_dag(result_dag)
                _save_dag(db, workflow_id, result_dag)
                _sync_steps(db, workflow_id, result_dag)
                _sync_projects_from_dag(db, workflow_id, result_dag)
                db.commit()

                context.pending_modification = None
                context.current_dag = result_dag
                suggestions = await _generate_proactive_suggestions(result_dag, context)
                response_text = f"已完成修改：{mod.description}"
                context.add_turn("agent", response_text, mod)
                return _make_response(response_text, result_dag, context, suggestions)

            except Exception as e:
                db.rollback()
                return _make_response(f"执行失败：{str(e)}", dag, context, [], error=str(e))

        # Fallback
        context.add_turn("agent", response_text, None)
        suggestions = await _generate_proactive_suggestions(dag, context)
        return _make_response(response_text, dag, context, suggestions)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
    finally:
        db_gen.close()

@router.get("/{workflow_id}/dag/conversation/history")
async def dag_conversation_history(workflow_id: str):
    """获取当前会话历史"""
    context = _get_or_create_context(workflow_id)
    return {
        "conversation_id": context.conversation_id,
        "history": [
            {"role": t.role, "content": t.content}
            for t in context.history
        ],
        "has_pending": context.pending_modification is not None,
    }

@router.post("/{workflow_id}/dag/conversation/reset")
async def dag_conversation_reset(workflow_id: str):
    """重置会话上下文"""
    from .dag_conversation_context import _conversation_store
    if workflow_id in _conversation_store:
        del _conversation_store[workflow_id]
    return {"status": "ok", "message": "会话已重置"}