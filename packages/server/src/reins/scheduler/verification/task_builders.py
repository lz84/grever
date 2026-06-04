"""
TaskBuilder — 构造验证任务 prompt。

根据不同 verifier_type 生成对应的验证指令，要求验证智能体
输出严格符合 JSON Schema 的结构化结果。
"""

class TaskBuilder:
    """根据任务信息和验证类型，生成验证智能体的执行 prompt。"""

    # ── 各验证类型的基础指令模板 ──────────────────────────
    _TYPE_PROMPTS = {
        "default": (
            "You are a verification agent. Review the task result and evidence "
            "against the acceptance criteria below."
        ),
        "code_test": (
            "You are a code verification agent. Check whether the submitted code "
            "compiles, passes tests, and meets functional requirements. "
            "Run available tests if possible, otherwise perform static analysis."
        ),
        "content_review": (
            "You are a content review agent. Evaluate whether the deliverable "
            "meets quality standards, completeness requirements, and aligns "
            "with the acceptance criteria."
        ),
        "analysis_check": (
            "You are an analysis verification agent. Validate the reasoning, "
            "data accuracy, and conclusions of the analytical work. "
            "Cross-check key claims against available evidence."
        ),
    }

    @staticmethod
    def build(
        task_id: str,
        result_summary: str,
        acceptance_criteria: list[str],
        artifacts: list[str],
        verifier_type: str = "default",
    ) -> str:
        """构造验证任务 prompt。

        Args:
            task_id:            任务唯一标识。
            result_summary:     任务执行结果摘要。
            acceptance_criteria: 验收标准列表，逐项验证。
            artifacts:          产出物列表（文件路径、URL 等）。
            verifier_type:      验证类型，可选
                                default / code_test / content_review / analysis_check。

        Returns:
            完整的验证任务 prompt 字符串，包含角色设定、验收标准、
            产出物清单以及严格的 JSON 输出格式要求。
        """
        role_instruction = TaskBuilder._TYPE_PROMPTS.get(
            verifier_type, TaskBuilder._TYPE_PROMPTS["default"]
        )

        # 逐条编号验收标准
        criteria_lines = "\n".join(
            f"  {idx}. {crit}" for idx, crit in enumerate(acceptance_criteria, 1)
        )

        # 产出物列表
        artifact_lines = "\n".join(
            f"  - {a}" for a in artifacts
        )

        prompt = f"""\
{role_instruction}

## Task ID
{task_id}

## Result Summary
{result_summary}

## Acceptance Criteria
Verify each of the following criteria and report whether it passes:
{criteria_lines}

## Artifacts
Review the following artifacts as evidence:
{artifact_lines}

## Output Format
You MUST output a single valid JSON object with NO additional text before or after it.
The JSON must follow this exact schema:

{{
    "passed": <boolean — true only if ALL acceptance criteria are met>,
    "message": "<string — brief summary of verification outcome, in Chinese>",
    "evidence": [
        {{
            "criteria_index": <1-based index of the acceptance criterion>,
            "criteria_text": "<the criterion text>",
            "status": "pass" | "fail" | "partial",
            "finding": "<what you observed>"
        }}
    ]
}}

The "evidence" array MUST contain one entry per acceptance criterion.
Do NOT include markdown code fences (```) or any extra text.
Output only the raw JSON."""

        return prompt
