"""
Workflow instantiation from Scenario endpoints.
"""

from fastapi import APIRouter, HTTPException, Body
from datetime import datetime
import json
import uuid
from loguru import logger
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from reins.common.database import get_db_manager
from sqlalchemy import text
from reach.scenarios.api._scen_instantiate_helpers import _evaluate_condition_preview, _determine_executor_behavior, _build_context_md, _create_hitl_request, _resolve_industry_dimension, _should_create_task
from .scenario_models import InstantiateWorkflowRequest, InstantiateWorkflowResponse, _parse_json

router = APIRouter(tags=["scenario-instantiate"])

class InstantiateToGoalRequest(BaseModel):
    goal_title: str
    goal_description: Optional[str] = None
    goal_priority: Optional[str] = "medium"
    goal_status: Optional[str] = "draft"

class InstantiateToGoalResponse(BaseModel):
    goal_id: str
    scenario_id: str
    projects_created: int
    tasks_created: int
    skipped: int

class PreviewTaskItem(BaseModel):
    name: str
    agent_type: Optional[str] = None
    required_capabilities: Optional[List[str]] = None

class PreviewProjectItem(BaseModel):
    id: str
    name: str
    tasks_count: int
    tasks: List[PreviewTaskItem]
    capability_tags: Optional[Dict[str, List[str]]] = None

class ScenarioPreviewResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    projects_count: int
    tasks_count: int
    projects: List[PreviewProjectItem]

@router.post("/api/v1/scenarios/{scenario_id}/instantiate-to-goal", response_model=InstantiateToGoalResponse)
def instantiate_to_goal(scenario_id: str, body: InstantiateToGoalRequest = Body(...)):
    """
    将场景实例化为 Goal（自动创建 Projects + Tasks）

    请求体:
    - goal_title: 目标标题
    - goal_description: 目标描述（可选）
    - goal_priority: 优先级（默认 medium）
    - goal_status: 状态（默认 draft）

    流程:
    1. 创建 Goal 并关联 scenario_id
    2. 从 scenario_steps 创建 Projects
    3. 从 scenario_tasks 创建 Tasks
    """
    db_manager = get_db_manager()
    engine = db_manager.engine
    now = datetime.now()

    with engine.connect() as conn:
        # 验证场景存在
        scenario = conn.execute(text("""
            SELECT id, name, category FROM scenarios WHERE id = :sid
        """), {"sid": scenario_id}).fetchone()

        if not scenario:
            raise HTTPException(404, f"Scenario not found: {scenario_id}")

        # 前置校验：场景必须包含 tasks，否则无法实例化
        task_count_check = conn.execute(text("""
            SELECT COUNT(*) FROM scenario_tasks WHERE scenario_id = :sid
        """), {"sid": scenario_id}).scalar() or 0

        if task_count_check == 0:
            raise HTTPException(
                400,
                f"Scenario '{scenario_id}' has no scenario_tasks defined. "
                f"Cannot instantiate an empty scenario — add tasks first."
            )

        # 先获取场景信息用于填充 context_md
        scenario_info = conn.execute(text("""
            SELECT id, name, category, scenario_desc FROM scenarios WHERE id = :sid
        """), {"sid": scenario_id}).fetchone()

        # 获取场景的 projects 和 tasks 数量
        project_count = conn.execute(text("""
            SELECT COUNT(*) FROM scenario_projects WHERE scenario_id = :sid
        """), {"sid": scenario_id}).scalar() or 0

        task_count = conn.execute(text("""
            SELECT COUNT(*) FROM scenario_tasks WHERE scenario_id = :sid
        """), {"sid": scenario_id}).scalar() or 0

        # 构建 context_md
        context_md_lines = [
            f"# {scenario_info.name}",
            f"",
            f"**类别**: {scenario_info.category}",
            f"**项目数**: {project_count}",
            f"**任务数**: {task_count}",
            f"",
        ]
        if scenario_info.scenario_desc:
            context_md_lines.append(f"{scenario_info.scenario_desc}")
            context_md_lines.append("")
        context_md_lines.append(f"从场景 `{scenario_id}` 实例化生成。")

        # 创建 Goal
        goal_id = f"goal-{uuid.uuid4().hex[:12]}"
        conn.execute(text("""
            INSERT INTO goals
            (id, title, description, priority, status, progress, created_at, updated_at,
             matched_scenario_id, task_ids, context_md)
            VALUES (:id, :title, :desc, :priority, :status, 0, :now, :now, :sid, '[]', :ctx)
        """), {
            "id": goal_id,
            "title": body.goal_title,
            "desc": body.goal_description or "",
            "priority": body.goal_priority,
            "status": body.goal_status,
            "now": now,
            "sid": scenario_id,
            "ctx": "\n".join(context_md_lines),
        })

        conn.commit()

    # 调用实例化逻辑（instantiate_scenario 已在本文件中定义，来自原 scenario_instantiate_v2）
    try:
        result = instantiate_scenario(goal_id, scenario_id, db_manager)
        logger.info(f"[Instantiate-to-Goal] Scenario {scenario_id} → Goal {goal_id}: {result}")

        return InstantiateToGoalResponse(
            goal_id=goal_id,
            scenario_id=scenario_id,
            projects_created=result["projects_created"],
            tasks_created=result["tasks_created"],
            skipped=result["skipped"],
        )
    except Exception as e:
        logger.error(f"[Instantiate-to-Goal] Failed: {e}")
        raise HTTPException(500, f"Instantiation failed: {str(e)}")

@router.get("/api/v1/scenarios/{scenario_id}/preview", response_model=ScenarioPreviewResponse)
def preview_scenario(scenario_id: str):
    """
    预览场景实例化结果 — 返回即将创建的 projects 和 tasks 结构，不实际创建。
    """
    db_manager = get_db_manager()
    engine = db_manager.engine

    with engine.connect() as conn:
        scenario = conn.execute(text("""
            SELECT id, name, category, scenario_desc FROM scenarios WHERE id = :sid
        """), {"sid": scenario_id}).fetchone()

        if not scenario:
            raise HTTPException(404, f"Scenario not found: {scenario_id}")

        # 获取 phases（从 scenario_tasks 按 phase_name 分组）
        phases_raw = conn.execute(text("""
            SELECT phase_name FROM scenario_tasks
            WHERE scenario_id = :sid
            GROUP BY phase_name
            ORDER BY MIN(order_in_phase) ASC
        """), {"sid": scenario_id}).fetchall()

        # 获取所有场景任务模板
        tasks_raw = conn.execute(text("""
            SELECT id, name, description, phase_name, required_capabilities,
                   dependencies, condition_type, condition_data, order_in_phase
            FROM scenario_tasks
            WHERE scenario_id = :sid
            ORDER BY phase_name ASC, order_in_phase ASC
        """), {"sid": scenario_id}).fetchall()

        # 按 phase_name 分组
        tasks_by_phase: Dict[str, List] = {}
        for t in tasks_raw:
            phase = t[3]  # phase_name
            if phase not in tasks_by_phase:
                tasks_by_phase[phase] = []
            tasks_by_phase[phase].append(t)

        # 构建预览结构（复用 instantiate_scenario 的逻辑，但不 INSERT）
        preview_projects: List[PreviewProjectItem] = []
        total_tasks = 0

        for phase_row in phases_raw:
            phase_name = phase_row[0]
            phase_tasks = tasks_by_phase.get(phase_name, [])
            if not phase_tasks:
                continue

            project_id = f"sp-{uuid.uuid4().hex[:8]}"
            preview_tasks: List[PreviewTaskItem] = []

            for t in phase_tasks:
                t_id, t_name, t_desc, t_phase, t_caps, t_deps, t_condition, t_cond_data, t_order = t

                # 复用条件判断逻辑
                should_create = _evaluate_condition_preview(t_condition, t_cond_data)
                if not should_create:
                    continue

                # 解析 required_capabilities
                req_caps = None
                if t_caps:
                    req_caps = json.loads(t_caps) if isinstance(t_caps, str) else t_caps

                preview_tasks.append(PreviewTaskItem(
                    name=t_name,
                    required_capabilities=req_caps,
                ))

            if not preview_tasks:
                continue

            # 聚合该 phase 下所有 task 的 required_capabilities 作为 project 的 capability_tags
            proj_professional = []
            for pt_item in preview_tasks:
                if pt_item.required_capabilities:
                    for cap in pt_item.required_capabilities:
                        if cap not in proj_professional:
                            proj_professional.append(cap)

            preview_projects.append(PreviewProjectItem(
                id=project_id,
                name=f"[{scenario.name}] {phase_name}",
                tasks_count=len(preview_tasks),
                tasks=preview_tasks,
                capability_tags={
                    "business": [],
                    "professional": proj_professional,
                    "technical": [],
                    "management": []
                },
            ))
            total_tasks += len(preview_tasks)

    return ScenarioPreviewResponse(
        scenario_id=scenario_id,
        scenario_name=scenario.name,
        projects_count=len(preview_projects),
        tasks_count=total_tasks,
        projects=preview_projects,
    )

def instantiate_scenario(goal_id: str, scenario_id: str, db_manager) -> Dict[str, Any]:
    """
    从场景蓝图实例化 Projects 和 Tasks。

    事务保证：Task 和 human_input_request 在同一事务中创建，
              要么都成功，要么都不创建（rollback）。

    Returns:
        {
            "projects_created": int,
            "tasks_created": int,
            "tasks_paused": int,
            "hitl_requests_created": int,
            "skipped": int,
        }
    """
    projects_created = 0
    tasks_created = 0
    tasks_waiting_human = 0
    hitl_requests_created = 0
    skipped = 0

    engine = db_manager.engine

    with engine.begin() as conn:
        # 1. 获取场景信息
        scenario = conn.execute(text("""
            SELECT id, name, category, scenario_desc FROM scenarios WHERE id = :sid
        """), {"sid": scenario_id}).fetchone()

        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        logger.info("[Instantiate] Goal %s referencing scenario %s", goal_id, scenario.name)

        # 更新 goal 的 matched_scenario_id
        now = datetime.now()
        conn.execute(text("""
            UPDATE goals SET matched_scenario_id = :sid, updated_at = :now WHERE id = :gid
        """), {"sid": scenario_id, "now": now, "gid": goal_id})

        # 2. 获取所有 phase_names
        phases_raw = conn.execute(text("""
            SELECT phase_name FROM scenario_tasks
            WHERE scenario_id = :sid
            GROUP BY phase_name
            ORDER BY MIN(order_in_phase) ASC
        """), {"sid": scenario_id}).fetchall()

        # 3. 获取所有场景任务模板（不含 agent_type）
        tasks_raw = conn.execute(text("""
            SELECT id, name, description, phase_name, required_capabilities,
                   dependencies, condition_type, condition_data, order_in_phase,
                   executor_type
            FROM scenario_tasks
            WHERE scenario_id = :sid
            ORDER BY phase_name ASC, order_in_phase ASC
        """), {"sid": scenario_id}).fetchall()

        # 按 phase_name 分组
        tasks_by_phase: Dict[str, List] = {}
        for t in tasks_raw:
            phase = t.phase_name
            if phase not in tasks_by_phase:
                tasks_by_phase[phase] = []
            tasks_by_phase[phase].append(t)

        # 4. 遍历 phase → 创建 projects
        prev_project_id = None

        for phase_row in phases_raw:
            phase_name = phase_row[0]
            phase_tasks = tasks_by_phase.get(phase_name, [])
            if not phase_tasks:
                continue

            project_id = f"proj-{uuid.uuid4().hex[:12]}"

            # 合并 required_capabilities → project capability_tags（按 dimension 分组）
            proj_all_caps = []
            for pt in phase_tasks:
                pt_caps_raw = pt[4]
                if pt_caps_raw:
                    caps = json.loads(pt_caps_raw) if isinstance(pt_caps_raw, str) else pt_caps_raw
                    for cap in caps:
                        if cap not in proj_all_caps:
                            proj_all_caps.append(cap)
            proj_capability_tags = json.dumps(_resolve_industry_dimension(proj_all_caps, conn))

            conn.execute(text("""
                INSERT INTO projects (id, name, description, goal_id, status,
                                     created_at, updated_at, assignee,
                                     depends_on, next_step, capability_tags)
                VALUES (:id, :name, :desc, :goal_id, 'active', :now, :now,
                        :assignee, :deps, '[]', :ctags)
            """), {
                "id": project_id,
                "name": f"[{scenario.name}] {phase_name}",
                "desc": phase_name,
                "goal_id": goal_id,
                "now": now,
                "assignee": phase_tasks[0].agent_type or "",
                "deps": json.dumps([prev_project_id]) if prev_project_id else "[]",
                "ctags": proj_capability_tags,
            })

            projects_created += 1

            # 更新上一步的 next_step
            if prev_project_id:
                conn.execute(text("""
                    UPDATE projects SET next_step = :next, updated_at = :now
                    WHERE id = :pid
                """), {
                    "next": json.dumps([project_id]),
                    "now": now,
                    "pid": prev_project_id,
                })

            # 5. 为该 phase 创建 tasks
            prev_task_id = None
            task_name_to_id: Dict[str, str] = {}

            for t in phase_tasks:
                # t: (id, name, description, phase_name, required_capabilities,
                #     dependencies, condition_type, condition_data, order_in_phase, executor_type)
                t_id = t[0]
                t_name = t[1]
                t_desc = t[2]
                t_caps = t[4]
                t_deps = t[5]
                t_condition = t[6]
                t_cond_data = t[7]
                t_executor_type = t[9] if len(t) > 9 else 'ai'

                # 条件评估（condition_type 优先级高于 executor_type）
                if not _should_create_task(t_condition, t_cond_data):
                    skipped += 1
                    continue

                # 根据 executor_type 决定状态和是否创建 HITL
                task_status, needs_hitl = _determine_executor_behavior(t_executor_type)
                if task_status == 'waiting_human':
                    tasks_waiting_human += 1

                task_uuid = f"task-{uuid.uuid4().hex[:12]}"

                # 解析依赖
                actual_deps = []
                raw_deps = json.loads(t_deps) if isinstance(t_deps, str) else (t_deps or [])
                for dep_name in raw_deps:
                    if dep_name in task_name_to_id:
                        actual_deps.append(task_name_to_id[dep_name])
                if prev_task_id and prev_task_id not in actual_deps:
                    actual_deps.append(prev_task_id)

                # required_capabilities → 四维 capability_tags（按 industry_capability_tags 表查 dimension）
                task_capability_tags = {
                    "business": [], "professional": [],
                    "technical": [], "management": [],
                }
                if t_caps:
                    caps_raw = json.loads(t_caps) if isinstance(t_caps, str) else t_caps
                    if isinstance(caps_raw, list):
                        task_capability_tags = _resolve_industry_dimension(caps_raw, conn)

                context_md = _build_context_md(
                    scenario.id, scenario.name, phase_name, t_name, project_id)

                executor_type_val = t_executor_type if t_executor_type else 'ai'

                conn.execute(text("""
                    INSERT INTO tasks (id, title, description, project_id, goal_id, status,
                                      priority, depends_on, next_step, assigned_agent,
                                      created_at, updated_at, needs_verification,
                                      capability_tags, context_md, executor_type)
                    VALUES (:id, :title, :desc, :project_id, :goal_id, :status,
                           2, :deps, '[]', :assignee, :now, :now, 0, :ctags,
                           :context_md, :executor_type)
                """), {
                    "id": task_uuid,
                    "title": t_name,
                    "desc": t_desc or "",
                    "project_id": project_id,
                    "goal_id": goal_id,
                    "status": task_status,
                    "deps": json.dumps(actual_deps) if actual_deps else "[]",
                    "assignee": "",
                    "now": now,
                    "ctags": json.dumps(task_capability_tags),
                    "context_md": context_md,
                    "executor_type": executor_type_val,
                })

                task_name_to_id[t_name] = task_uuid
                tasks_created += 1

                # 创建 HITL request（幂等保护，同一事务内）
                if needs_hitl:
                    created = _create_hitl_request(
                        conn, task_uuid, goal_id, project_id,
                        t_name, t_desc, executor_type_val,
                        scenario.id, scenario.name)
                    if created:
                        hitl_requests_created += 1

                # 更新上一步的 next_step
                if prev_task_id:
                    conn.execute(text("""
                        UPDATE tasks SET next_step = :next, updated_at = :now
                        WHERE id = :tid
                    """), {
                        "next": json.dumps([task_uuid]),
                        "now": now,
                        "tid": prev_task_id,
                    })

                prev_task_id = task_uuid

            prev_project_id = project_id

        # engine.begin() 自动 commit；异常自动 rollback
        # 显式 commit 用于确认
        conn.commit()

    logger.info(
        "[Instantiate] done: %d projects, %d tasks (%d waiting_human), "
        "%d HITL requests, %d skipped",
        projects_created, tasks_created, tasks_waiting_human,
        hitl_requests_created, skipped)

    return {
        "projects_created": projects_created,
        "tasks_created": tasks_created,
        "tasks_waiting_human": tasks_waiting_human,
        "hitl_requests_created": hitl_requests_created,
        "skipped": skipped,
    }

def _resolve_industry_dimension(tag_ids: List[str], conn) -> Dict[str, List[str]]:
    """
    查询 industry_capability_tags 表，按 dimension 将标签 ID 分组。

    Returns:
        {"business": [], "professional": [], "technical": [], "management": []}
    未知标签安全降级到 "professional"（向后兼容）。
    """
    result: Dict[str, List[str]] = {
        "business": [], "professional": [], "technical": [], "management": [],
    }
    if not tag_ids:
        return result

    placeholders = ",".join(f":i{i}" for i in range(len(tag_ids)))
    params = {f"i{i}": tid for i, tid in enumerate(tag_ids)}
    rows = conn.execute(text(f"""
        SELECT id, dimension FROM industry_capability_tags
        WHERE id IN ({placeholders})
    """), params).fetchall()

    found_ids = set()
    for row_id, dimension in rows:
        dim = dimension if dimension in result else "professional"
        result[dim].append(row_id)
        found_ids.add(row_id)

    # 未知标签降级到 professional
    for tid in tag_ids:
        if tid not in found_ids:
            result["professional"].append(tid)

    return result

def _should_create_task(condition_type: Optional[str],
                        condition_data: Optional[str]) -> bool:
    """
    评估 condition_type 决定是否创建该 task。

    - 'none' / None → 创建
    - 'auto_eval'   → 创建（当前简化处理）
    - 'human_decision' / 'human_input' → 跳过（由 HITL 流程处理）
    """
    if not condition_type or condition_type == 'none':
        return True
    if condition_type == 'auto_eval':
        return True
    # human_decision / human_input → 不在此创建
    return False

