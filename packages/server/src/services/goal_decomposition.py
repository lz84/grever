"""
目标自动分解服务

使用 LLM 将 Goal 自动分解为带 DAG 依赖关系的 Task 列表。

P5-2: category 字段已替换为 capability_tags（四维标签体系）
P5-4: context_md 在任务创建时自动填充
"""

import json
from loguru import logger
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from .llm_service import llm_service
from models.task import Task, TaskDependency

# P5-2: 系统提示词已更新，使用 capability_tags 替代 category
DECOMPOSITION_SYSTEM_PROMPT = """你是一个专业的项目分解专家。你的任务是将一个高层目标（Goal）分解为可执行的、有依赖关系的任务（Task）列表。

要求：
1. 每个任务应该是具体的、可衡量的、可在单个 Agent 执行周期内完成
2. 任务之间应该有清晰的依赖关系（DAG 结构）
3. 先做研究/设计类任务，再做实现类任务，最后做验证类任务
4. 任务数量通常在 3-8 个之间，不要过度分解
5. 为每个任务指定优先级（low/medium/high）
6. 为每个任务指定能力标签（四维：business/professional/technical/management 中的相关标签）

返回格式必须是严格的 JSON：
{
  "tasks": [
    {
      "title": "任务标题",
      "description": "任务详细描述",
      "priority": "high|medium|low",
      "capability_tags": {
        "business": ["相关业务能力标签"],
        "professional": ["相关专业能力标签"],
        "technical": ["相关技术能力标签"],
        "management": ["相关管理能力标签"]
      },
      "depends_on": [依赖的任务索引，从 0 开始]
    }
  ]
}

注意：
- depends_on 使用数组中的索引（0-based），不是任务 ID
- 第一个任务通常没有依赖
- 确保依赖关系不会形成循环
- capability_tags 四个维度都要包含，没有相关标签则用空数组 []"""

# 默认四维能力标签（当 LLM 未返回时使用）
_DEFAULT_CAPABILITY_TAGS = {
    "business": [],
    "professional": [],
    "technical": [],
    "management": [],
}


def decompose_goal(goal_title: str, goal_description: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    使用 LLM 分解目标为任务列表

    Args:
        goal_title: 目标标题
        goal_description: 目标描述（可选）

    Returns:
        任务列表，每个任务包含 title, description, priority, capability_tags, depends_on
    """
    user_prompt = f"请将以下目标分解为可执行的任务：\n\n目标标题：{goal_title}"
    if goal_description:
        user_prompt += f"\n\n目标描述：{goal_description}"
    user_prompt += "\n\n请返回 JSON 格式的任务分解结果。"

    messages = [
        {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = llm_service.chat_completion(
            messages,
            response_format={"type": "json_object"},
        )

        # 尝试解析 JSON
        # 处理可能的 markdown 代码块
        if response.startswith("```"):
            # 提取 JSON 部分
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != 0:
                response = response[start:end]

        result = json.loads(response)
        tasks = result.get("tasks", [])

        if not tasks:
            logger.warning(f"LLM 返回的任务列表为空，目标: {goal_title}")
            return []

        # 验证任务结构
        validated_tasks = []
        for i, task in enumerate(tasks):
            validated_task = {
                "title": task.get("title", f"任务 {i+1}"),
                "description": task.get("description", ""),
                "priority": task.get("priority", "medium"),
                # P5-2: 使用 capability_tags 替代 category
                "capability_tags": task.get("capability_tags", dict(_DEFAULT_CAPABILITY_TAGS)),
                "depends_on": task.get("depends_on", []),
            }
            # 确保优先级有效
            if validated_task["priority"] not in ("low", "medium", "high"):
                validated_task["priority"] = "medium"
            # P5-2: 确保 capability_tags 是有效的四维字典
            tags = validated_task["capability_tags"]
            if not isinstance(tags, dict):
                tags = dict(_DEFAULT_CAPABILITY_TAGS)
            for dim in ("business", "professional", "technical", "management"):
                if dim not in tags:
                    tags[dim] = []
                elif not isinstance(tags[dim], list):
                    tags[dim] = [str(tags[dim])] if tags[dim] else []
            validated_task["capability_tags"] = tags
            # 确保 depends_on 是整数列表
            validated_task["depends_on"] = [
                idx for idx in validated_task["depends_on"]
                if isinstance(idx, int) and 0 <= idx < i
            ]
            validated_tasks.append(validated_task)

        logger.info(f"目标分解成功: {goal_title} → {len(validated_tasks)} 个任务")
        return validated_tasks

    except json.JSONDecodeError as e:
        logger.error(f"LLM 返回的 JSON 解析失败: {e}")
        raise ValueError(f"LLM 返回格式无效: {e}")
    except Exception as e:
        logger.error(f"目标分解失败: {e}")
        raise


def _build_decomposition_context_md(goal_id: Any, goal_title: str, task_name: str) -> str:
    """P5-4: 为分解产生的任务构建 context_md"""
    ctx = {
        "source": "goal_decomposition",
        "goal_id": str(goal_id),
        "goal_title": goal_title,
        "task_name": task_name,
    }
    return json.dumps(ctx, ensure_ascii=False)


def create_tasks_from_decomposition(
    goal_id: Any,
    tasks: List[Dict[str, Any]],
    db: Session,
    goal_title: str = "",
    parent_id: Optional[Any] = None,
) -> List[Task]:
    """
    根据分解结果创建任务和依赖关系

    Args:
        goal_id: 所属目标 ID
        tasks: 分解得到的任务列表
        db: 数据库会话
        goal_title: 目标标题（用于填充 context_md）
        parent_id: 可选的父任务 ID

    Returns:
        创建的任务列表
    """
    from reins.scheduler.task_assigner import _assign_agent

    created_tasks: List[Task] = []

    for task_data in tasks:
        # 创建时自动分配 Agent（谁创建谁分派）
        agent_id = _assign_agent(db)
        if not agent_id:
            logger.warning(f"[goal_decomposition] No online agent available for goal {goal_id}")

        # P5-2: 将 capability_tags 序列化为 JSON 字符串
        capability_tags = task_data.get("capability_tags", dict(_DEFAULT_CAPABILITY_TAGS))
        tags_json = json.dumps(capability_tags) if isinstance(capability_tags, dict) else tags_json

        # P5-4: 构建 context_md
        context_md = _build_decomposition_context_md(goal_id, goal_title, task_data["title"])

        task = Task(
            title=task_data["title"],
            description=task_data["description"],
            priority=task_data["priority"],
            capability_tags=tags_json,
            goal_id=goal_id,
            parent_id=parent_id,
            status="todo",
            assigned_agent=agent_id,
            context_md=context_md,
        )
        db.add(task)
        created_tasks.append(task)

    # 先 flush 以获取 task ID
    db.flush()

    # 创建依赖关系
    for i, task_data in enumerate(tasks):
        task = created_tasks[i]
        for dep_idx in task_data.get("depends_on", []):
            if 0 <= dep_idx < len(created_tasks):
                dependency = TaskDependency(
                    task_id=task.id,
                    dependency_id=created_tasks[dep_idx].id,
                )
                db.add(dependency)

    db.commit()

    # 刷新所有任务以获取完整的 ID
    for task in created_tasks:
        db.refresh(task)

    logger.info(f"为 goal_id={goal_id} 创建了 {len(created_tasks)} 个任务和对应的依赖关系")
    return created_tasks


def decompose_and_create_tasks(
    goal_id: Any,
    goal_title: str,
    goal_description: Optional[str],
    db: Session,
    parent_id: Optional[Any] = None,
) -> List[Task]:
    """
    完整的目标分解流程：LLM 分解 → 创建任务和依赖关系

    Args:
        goal_id: 目标 ID
        goal_title: 目标标题
        goal_description: 目标描述
        db: 数据库会话
        parent_id: 可选的父任务 ID

    Returns:
        创建的任务列表

    Raises:
        ValueError: 当 LLM 返回无效格式时
        Exception: 当 LLM 调用失败时
    """
    # 步骤 1: LLM 分解
    tasks = decompose_goal(goal_title, goal_description)

    if not tasks:
        logger.warning(f"目标分解返回空结果: {goal_title}")
        return []

    # 步骤 2: 创建任务和依赖关系
    created_tasks = create_tasks_from_decomposition(
        goal_id, tasks, db,
        goal_title=goal_title,
        parent_id=parent_id,
    )

    return created_tasks
