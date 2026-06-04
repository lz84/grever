"""知识注入 API - Cognition 生成逻辑"""

from typing import Dict
from .knowledge_injector_models import TaskResultInput, WorkflowResultInput, DisputeResultInput

def _generate_cognition_from_task(result: TaskResultInput) -> Dict:
    """将任务执行结果转换为 Cognition 格式"""
    if result.status == "completed":
        cognition_type = "pattern"
        content = f"[成功模式] 任务「{result.task_title}」由 {result.agent_name or result.agent_id or '未知'} 成功完成。"
        if result.output_summary:
            content += f"\n\n输出摘要：{result.output_summary}"
        if result.duration_ms:
            content += f"\n\n耗时：{result.duration_ms}ms"
        tags = (result.tags or []) + ["task_success", "pattern"]
    elif result.status == "failed":
        cognition_type = "lesson"
        content = f"[失败教训] 任务「{result.task_title}」由 {result.agent_name or result.agent_id or '未知'} 执行失败。"
        if result.error_message:
            content += f"\n\n错误信息：{result.error_message}"
        tags = (result.tags or []) + ["task_failure", "lesson"]
    else:
        cognition_type = "meta"
        content = f"[任务元数据] 任务「{result.task_title}」状态：{result.status}。"
        tags = (result.tags or []) + ["task_meta"]

    return {
        "type": cognition_type,
        "content": content,
        "tags": list(set(tags)),
        "source": {
            "agent_id": result.agent_id or "nexus",
            "agent_name": result.agent_name,
            "task_id": result.task_id,
            "workflow_id": result.workflow_id,
            "goal_id": result.goal_id,
            "project_id": result.project_id,
            "channel": "nexus_api",
        },
        "confidence": 0.9 if result.status == "completed" else 0.7,
    }

def _generate_cognition_from_workflow(result: WorkflowResultInput) -> Dict:
    """将工作流执行结果转换为 Cognition 格式"""
    completion_rate = (result.completed_tasks / result.total_tasks * 100) if result.total_tasks > 0 else 0

    if result.status == "completed":
        cognition_type = "meta"
        content = (
            f"[流程元数据] 工作流「{result.workflow_name}」已完成。"
            f"\n\n任务完成率：{completion_rate:.1f}% ({result.completed_tasks}/{result.total_tasks})"
            f"\n失败任务：{result.failed_tasks}"
        )
        if result.disputes_resolved:
            content += f"\n解决争议：{result.disputes_resolved} 次"
        if result.duration_ms:
            content += f"\n总耗时：{result.duration_ms}ms"
        tags = (result.tags or []) + ["workflow_completed", "meta", "process_insight"]
    else:
        cognition_type = "lesson"
        content = (
            f"[流程教训] 工作流「{result.workflow_name}」执行状态：{result.status}。"
            f"\n\n任务完成率：{completion_rate:.1f}% ({result.completed_tasks}/{result.total_tasks})"
        )
        tags = (result.tags or []) + ["workflow_failure", "lesson"]

    return {
        "type": cognition_type,
        "content": content,
        "tags": list(set(tags)),
        "source": {
            "agent_id": "nexus",
            "workflow_id": result.workflow_id,
            "goal_id": result.goal_id,
            "channel": "nexus_api",
        },
        "confidence": 0.85,
    }

def _generate_cognition_from_dispute(result: DisputeResultInput) -> Dict:
    """将争议解决结果转换为 Cognition 格式"""
    cognition_type = "lesson"
    content = f"[冲突处理经验] 争议类型：{result.dispute_type}，解决方式：{result.resolution}。"
    if result.summary:
        content += f"\n\n争议摘要：{result.summary}"
    if result.lesson_learned:
        content += f"\n\n教训：{result.lesson_learned}"
    if result.resolution_time_ms:
        content += f"\n解决耗时：{result.resolution_time_ms}ms"

    tags = ["dispute_resolution", "lesson", result.dispute_type]
    if result.agent_ids:
        tags.extend(result.agent_ids)

    return {
        "type": cognition_type,
        "content": content,
        "tags": list(set(tags)),
        "source": {
            "agent_id": "nexus",
            "dispute_id": result.dispute_id,
            "task_id": result.task_id,
            "agent_ids": result.agent_ids,
            "channel": "nexus_api",
        },
        "confidence": 0.8,
    }
