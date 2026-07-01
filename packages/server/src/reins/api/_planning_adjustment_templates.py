# -*- coding: utf-8 -*-
"""
PA-1 / PA-2 Prompt 模板常量 — 规划调整模块 Sprint 6 s6-4

这些模板会被 seed_pa_templates() 写入 prompt_library 表。
"""

PA1_TEMPLATE = """你收到一个规划调整请求。以下是调整的原因和上下文：
- 调整原因：{adjustment_reason}
- 反馈摘要：{feedback_summary}

当前 Goal 的上下文：
{context_md}

当前规划（confirmed_plan）：
{confirmed_plan}

请评估是否需要调整当前规划。如果需要，请给出：
1. 调整类型（目标重设 / 依赖重排 / 范围缩减 / 新增任务）
2. 具体调整方案（JSON 格式，包含 changes 数组）
3. 调整理由

如果不需要调整，请明确说明"不需要调整"，并简述理由。

请以 JSON 格式返回，schema 如下：
{{
  "needs_adjustment": true|false,
  "adjustment_type": "goal_reset|dep_reorder|scope_reduce|new_tasks|none",
  "changes": [
    {{
      "type": "add|remove|modify|reorder",
      "target": "task_id 或 project_id",
      "description": "调整说明"
    }}
  ],
  "rationale": "调整理由或不需要调整的理由"
}}"""

PA2_TEMPLATE = """Coordinator Agent 评估结果：

{coordinator_response}

基于以上评估，请：
1. 如果 needs_adjustment = true：输出最终的调整方案（JSON 格式）
2. 如果 needs_adjustment = false：输出"规划保持不变"及理由

最终调整方案格式：
{{
  "decision": "adjust|keep",
  "adjustment_plan": {{
    "type": "goal_reset|dep_reorder|scope_reduce|new_tasks",
    "changes": [...],
    "expected_outcome": "调整后的预期效果"
  }},
  "keep_rationale": "保持原规划的理由（如果 decision=keep）"
}}"""

PA1_CONTEXT_SCHEMA = {
    "adjustment_reason": {"type": "string", "required": True},
    "feedback_summary": {"type": "string", "required": True},
    "context_md": {"type": "string", "required": False},
    "confirmed_plan": {"type": "string", "required": False},
}

PA1_OUTPUT_SCHEMA = {
    "needs_adjustment": {"type": "boolean", "required": True},
    "adjustment_type": {"type": "string", "required": False},
    "changes": {"type": "array", "required": False},
    "rationale": {"type": "string", "required": False},
}
