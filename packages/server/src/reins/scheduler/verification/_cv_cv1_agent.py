"""CV-1 Agent interaction — prompt building, calling, output parsing."""
import asyncio
import json
import re
from typing import Any, Dict

from loguru import logger


def build_cv1_prompt(target_id: str, level: str, context: Dict[str, Any]) -> str:
    """构建 CV-1 统筹验证 Prompt。"""
    level_label = "Project" if level == "project" else "Goal"

    if level == "project":
        target_info = context["project"]
        task_summary = "\n".join(
            f"- [{t['status']}] {t['title']}: {t['result_summary'][:200]}"
            for t in context["tasks"]
        )
        met = context["all_tasks_done"]
        note = (
            f"前置条件已满足：{context['done_tasks']}/{context['total_tasks']} Tasks done"
            if met else f"前置条件未完全满足：{context['done_tasks']}/{context['total_tasks']} Tasks done"
        )
    else:
        target_info = context["goal"]
        task_summary = "\n".join(
            f"- [{p['status']}] {p['name']} ({p['done_tasks']}/{p['total_tasks']} Tasks done)"
            for p in context["projects"]
        )
        met = context["all_projects_completed"]
        note = "前置条件已满足：所有 Projects 完成" if met else "前置条件未完全满足"

    planning = ""
    for ps in context.get("planning_sessions", []):
        if ps.get("confirmed_plan"):
            planning += f"\n### Session {ps['id']} ({ps['status']})\n"
            plan = ps["confirmed_plan"]
            if isinstance(plan, dict):
                planning += f"计划项目: {plan.get('projects', [])}\n"

    return f"""# 统筹验证 - CV-1 模板

## 验证目标
**类型**: {level_label}
**ID**: {target_id}
**名称**: {target_info.get('name') or target_info.get('title')}
**描述**: {target_info.get('description', '') or target_info.get('title', '')}

{note}

## 下属任务/项目汇总
{task_summary or '（无）'}

## 计划历史
{planning or '（无）'}

## 三级上下文
```
{target_info.get('context_md', '（无）') or '（无）'}
```

## 验证要求
1. **业务闭环**: 所有 Task 的产出是否形成了完整的业务价值？
2. **跨任务一致性**: Task 之间是否有矛盾或重复？
3. **目标对齐**: 所有产出是否真正对齐 {level_label} 的目标？
4. **质量门槛**: 产出质量是否达到预期标准？

## 输出格式（JSON）
```json
{{
  "verdict": "passed" | "failed" | "partial",
  "summary": "验证结论摘要",
  "task_results": {{"passed": [], "failed": [], "partial": []}},
  "gaps": [],
  "recommendations": [],
  "remedial_tasks": []
}}
```
"""


async def call_cv1_agent(agent_id: str, prompt: str) -> str:
    """通过 OpenClaw sessions_spawn 调用 CV-1 Agent。"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "openclaw", "sessions", "spawn",
            "--agent", agent_id, "--wait", "--prompt", prompt,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode == 0:
            return stdout.decode("utf-8", errors="replace")
        else:
            logger.warning("[CV-1] Agent call failed: rc=%d", proc.returncode)
            return json.dumps({
                "verdict": "failed", "summary": f"Agent 调用失败（rc={proc.returncode}）",
                "task_results": {"passed": [], "failed": [], "partial": []},
                "gaps": [{"gap": "Agent 调用失败", "severity": "high", "task_ids": []}],
                "recommendations": [], "remedial_tasks": [],
            })
    except asyncio.TimeoutError:
        return json.dumps({"verdict": "failed", "summary": "Agent 调用超时",
                           "task_results": {"passed": [], "failed": [], "partial": []},
                           "gaps": [], "recommendations": [], "remedial_tasks": []})
    except Exception as e:
        logger.error(f"[CV-1] Agent call error: {e}")
        return json.dumps({"verdict": "failed", "summary": str(e),
                           "task_results": {"passed": [], "failed": [], "partial": []},
                           "gaps": [], "recommendations": [], "remedial_tasks": []})


def parse_cv1_output(raw_output: str) -> Dict[str, Any]:
    """解析 CV-1 Agent 的原始输出，提取 JSON 结果。"""
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw_output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    first, last = raw_output.find("{"), raw_output.rfind("}")
    if first != -1 and last > first:
        try:
            return json.loads(raw_output[first:last + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("[CV-1] Failed to parse output as JSON")
    return {
        "verdict": "failed", "summary": "无法解析 CV-1 输出",
        "task_results": {"passed": [], "failed": [], "partial": []},
        "gaps": [{"gap": "CV-1 输出解析失败", "severity": "high", "task_ids": []}],
        "recommendations": [], "remedial_tasks": [],
    }
