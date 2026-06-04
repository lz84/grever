"""LLM 意图解析 + 降级正则匹配"""

import json
import re
from typing import Optional

from .dag_conversation_context import ConversationContext, DAGModification

def _format_dag_for_llm(dag: dict) -> str:
    """把 DAG 格式化为文本，供 LLM 分析"""
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])

    if not nodes:
        return "当前工作流为空，尚未有任何阶段。"

    node_lines = []
    for n in nodes:
        title = n.get("data", {}).get("title", n.get("label", n.get("title", "未命名")))
        node_lines.append(f"  - [{n['id']}] {title}")

    edge_lines = []
    for e in edges:
        src = e.get("source", e.get("from", "?"))
        tgt = e.get("target", e.get("to", "?"))
        edge_lines.append(f"  - {src} → {tgt}")

    return (
        f"【节点】（共 {len(nodes)} 个）：\n" + "\n".join(node_lines)
        + f"\n\n【连线】（共 {len(edges)} 条）：\n"
        + ("\n".join(edge_lines) if edge_lines else "  （无连线）")
    )

async def _parse_intent_with_llm(
    user_message: str,
    dag: dict,
    context: ConversationContext,
) -> dict:
    """使用 LLM 理解用户的自然语言意图。"""
    try:
        from services.llm_service import llm_service
    except ImportError:
        return _fallback_parse_intent(user_message, dag)

    dag_text = _format_dag_for_llm(dag)
    history_text = context.get_history_text()

    system_prompt = f"""你是应急管理工作流的 AI 助手"刚子"，善于通过对话理解用户需求并改进工作流。

当前工作流 DAG 信息：
{dag_text}

对话历史：
{history_text}

用户可能会说的话：
- 模糊的需求："我觉得应急响应这块少了点什么"、"流程好像不太对"
- 具体的修改："在阶段1后面加一个资源评估"、"删掉阶段3"、"把阶段2改名为专家评审"
- 确认："可以"、"好"、"执行"、"对"、"行"
- 取消："算了"、"不要了"、"取消"

分析用户意图并严格返回 JSON：

若用户表达模糊需求（不确定想改什么）：
{{"intent_type": "ask_clarify", "confidence": 0.6, "response": "我理解你的担忧...", "follow_up": "具体问题"}}

若用户意图清晰可以提出具体修改建议：
{{"intent_type": "suggest", "confidence": 0.85, "response": "我理解你的意思。", "action": "insert_after", "params": {{"ref_node_id": "phase-1", "new_title": "资源评估", "new_desc": "评估人员伤亡、基础设施损毁等"}}, "description": "在阶段1后面插入资源评估"}}

若用户确认执行：
{{"intent_type": "execute", "confidence": 0.95, "response": "好的，正在执行修改..."}}

若用户取消：
{{"intent_type": "cancel", "confidence": 0.95, "response": "好的，已取消本次修改。"}}

严格返回 JSON，不要有其他内容。"""

    try:
        response = await llm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=512,
        )

        text = response.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())
        return {
            "response": result.get("response", ""),
            "intent_type": result.get("intent_type", "ask_clarify"),
            "confidence": result.get("confidence", 0.5),
            "action": result.get("action"),
            "params": result.get("params", {}),
            "description": result.get("description", ""),
            "follow_up": result.get("follow_up"),
        }
    except Exception:
        return _fallback_parse_intent(user_message, dag)

def _fallback_parse_intent(user_message: str, dag: dict) -> dict:
    """LLM 不可用时的降级解析（正则+关键词匹配）"""
    msg = user_message.strip().lower()

    # 确认
    confirm_kw = ["可以", "好", "执行", "对", "行", "确定", "ok", "yes", "execute"]
    if any(k in msg for k in confirm_kw):
        return {
            "intent_type": "execute", "confidence": 0.9,
            "response": "好的，正在执行...", "action": None
        }

    # 取消
    cancel_kw = ["算了", "不要", "取消", "no", "cancel"]
    if any(k in msg for k in cancel_kw):
        return {
            "intent_type": "cancel", "confidence": 0.9,
            "response": "好的，已取消。", "action": None
        }

    # 插入节点: "在{name}后面加{new}"
    m = re.search(r"在(.+?)(?:后面|之前|前|后)加", msg)
    if m:
        ref = m.group(1).strip()
        new_m = re.search(r"加(.+?)$", msg)
        new_title = new_m.group(1).strip() if new_m else "新环节"
        return {
            "intent_type": "suggest", "confidence": 0.7,
            "response": f"好的，我理解你想在{ref}后面加一个新环节：{new_title}",
            "action": "insert_after",
            "params": {"ref_node_id": ref, "new_title": new_title},
            "description": f"在{ref}后面插入{new_title}",
        }

    # 删除节点
    m = re.search(r"(?:删|删除|去掉)(.+?)(?:阶段|环节|节点|$)", msg)
    if m:
        node = m.group(1).strip()
        return {
            "intent_type": "suggest", "confidence": 0.7,
            "response": f"好的，我理解你想删除节点：{node}",
            "action": "delete_node",
            "params": {"node_id": node},
            "description": f"删除节点：{node}",
        }

    # 重命名
    m = re.search(r"把(.+?)改名为(.+?)$", msg)
    if m:
        old, new = m.group(1).strip(), m.group(2).strip()
        return {
            "intent_type": "suggest", "confidence": 0.7,
            "response": f"好的，我理解你想把{old}改名为{new}",
            "action": "rename_node",
            "params": {"node_id": old, "new_title": new},
            "description": f"把{old}改名为{new}",
        }

    return {
        "intent_type": "ask_clarify", "confidence": 0.5,
        "response": "我理解你的意思。能说得更具体一些吗？比如'在XX后面加一个环节'或者'删掉XX'？",
        "action": None,
    }

async def _generate_proactive_suggestions(
    dag: dict,
    context: ConversationContext,
) -> list:
    """分析当前 DAG 结构，主动发现可能的改进空间。"""
    try:
        from services.llm_service import llm_service
    except ImportError:
        return []

    dag_text = _format_dag_for_llm(dag)

    system_prompt = f"""你是应急管理工作流的 AI 助手"刚子"。

当前工作流 DAG 信息：
{dag_text}

请分析这个工作流，找出 0-3 个最值得关注的改进建议。常见的检查项：
1. 是否有缺失的关键环节（如：资源评估、专家会商、事后总结）
2. 节点之间的依赖是否合理
3. 是否缺少结束或复盘环节

请严格返回 JSON 数组，格式：
[
  {{"title": "建议标题", "reason": "为什么提这个建议", "action": "insert_after", "params": {{"ref_node_id": "阶段ID", "new_title": "新节点标题"}}, "confidence": 0.8}}
]
如果没有明显问题，返回空数组 []。"""

    try:
        response = await llm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请分析当前工作流，告诉我哪些地方可以改进"}
            ],
            temperature=0.3,
            max_tokens=512,
        )

        text = response.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        suggestions = json.loads(text.strip())
        return suggestions if isinstance(suggestions, list) else []
    except Exception:
        return []