"""Task API helpers — extracted from tasks.py"""
from loguru import logger
import json
from typing import Optional, Dict, Any

def _validate_task_constraints(task_data) -> Optional[str]:
    """
    验证任务数据:
    - description 长度 ≤ 200 字
    - acceptance_criteria JSON 中 criteria 数量 ≤ 3 条
    - depends_on 必须设置（可为空列表）
    - capability_tags 必须设置（四维标签字典）
    返回错误消息,None 表示验证通过
    """
    description = getattr(task_data, 'description', None)
    if description and len(description) > 200:
        return (
            f"description 过长 ({len(description)} 字),Doc Refs Mode 要求 ≤ 200 字。"
            f"请将详细设计写入文档并通过 doc_refs 引用。"
        )

    # Sprint 85: depends_on 必须显式设置（仅 TaskCreate）
    # TaskUpdate 时 depends_on 可选（exclude_unset=True 时不验证）
    depends_on = getattr(task_data, 'depends_on', None)
    unset_fields = task_data.model_dump(exclude_unset=True) if hasattr(task_data, 'model_dump') else {}
    if 'depends_on' in unset_fields and depends_on is None:
        return "depends_on 必须设置（可为空列表 []），用于明确 DAG 执行顺序"

    # Sprint 85: capability_tags 必须设置（仅 TaskCreate）
    # TaskUpdate 时 capability_tags 可选
    # Bug fix: 当有 project_id 时允许为空，因为后端会从 Project 继承 capability_tags
    capability_tags = getattr(task_data, 'capability_tags', None)
    project_id = getattr(task_data, 'project_id', None)
    if 'capability_tags' in unset_fields and not capability_tags and not project_id:
        return "capability_tags 必须设置（四维标签字典），用于匹配引擎分配 Agent。如果关联了 Project，将自动从 Project 继承。"
    if isinstance(capability_tags, str):
        try:
            capability_tags = json.loads(capability_tags)
        except (json.JSONDecodeError, TypeError):
            return "capability_tags JSON 格式无效"
    if isinstance(capability_tags, dict):
        valid_dims = {"business", "professional", "technical", "management"}
        for key in capability_tags:
            if key not in valid_dims:
                return f"capability_tags 包含无效维度 '{key}'，有效维度: {valid_dims}"

    acceptance_criteria = getattr(task_data, 'acceptance_criteria', None)
    if acceptance_criteria:
        try:
            criteria_data = json.loads(acceptance_criteria)
            criteria_list = criteria_data.get("criteria", []) if isinstance(criteria_data, dict) else []
            if len(criteria_list) > 3:
                return (
                    f"acceptance_criteria 中 criteria 数量过多 ({len(criteria_list)} 条),"
                    f"Doc Refs Mode 要求 ≤ 3 条。请将详细验收标准写入文档并通过 doc_refs 引用。"
                )
        except (json.JSONDecodeError, TypeError):
            pass

    return None

def _update_goal_progress(db, goal_id: str) -> Optional[dict]:
    """
    统一更新 Goal 进度。
    基于该 goal 下所有 task 的完成状态计算百分比。
    """
    from models.goal import Goal as GoalModel
    from models.task import Task
    from models.project import Project
    from datetime import datetime
    from reins.scheduler.statemachine import GoalStateMachine

    goal = db.query(GoalModel).filter(GoalModel.id == goal_id).first()
    if not goal:
        return None

    all_tasks = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(Project.goal_id == goal_id)
        .all()
    )
    total_tasks = len(all_tasks)
    if total_tasks == 0:
        return {"goal_id": goal_id, "completed_tasks": 0, "total_tasks": 0, "progress_percent": 0.0}

    completed_tasks = sum(1 for t in all_tasks if t.status in ("done", "completed"))
    blocked_tasks = sum(1 for t in all_tasks if t.status == "blocked")
    progress_percent = round((completed_tasks / total_tasks * 100), 2)

    goal.progress = progress_percent
    goal.updated_at = datetime.now()

    # 通过状态机处理状态变更
    fsm = GoalStateMachine(db, goal_id)
    if completed_tasks == total_tasks:
        fsm.transition("completed", reason="所有任务完成", extra={"completed_at": datetime.now(), "updated_at": int(datetime.now().timestamp())})
    elif blocked_tasks > 0:
        fsm.transition("failed", reason="存在阻塞任务", extra={"updated_at": int(datetime.now().timestamp())})

    return {
        "goal_id": goal_id,
        "completed_tasks": completed_tasks,
        "total_tasks": total_tasks,
        "progress_percent": progress_percent,
    }

def _get_goal_id_from_project(db, project_id: Optional[str]) -> Optional[str]:
    """通过 project_id 推导 goal_id(task 不再直接关联 goal)"""
    if not project_id:
        return None
    from models.project import Project
    project = db.query(Project.goal_id).filter(Project.id == project_id).first()
    return project[0] if project else None

def _parse_agent_result(result: str) -> Dict[str, Any]:
    """
    解析代理结果以检测人类输入需求。
    功能:
    1. 尝试解析结果为JSON
    2. 检测 needs_human_input 字段
    3. 提取 input_type, schema, description
    4. 如果检测到,返回解析的字典
    5. 如果不是JSON,返回空字典
    """
    try:
        parsed_result = json.loads(result)
        if isinstance(parsed_result, dict) and parsed_result.get("needs_human_input"):
            return {
                "needs_human_input": True,
                "input_type": parsed_result.get("input_type", "confirmation"),
                "schema": parsed_result.get("schema", {}),
                "description": parsed_result.get("description", parsed_result.get("message", "")),
                "title": parsed_result.get("title", "Human Input Required"),
                "context": parsed_result.get("context", {}),
            }
        return {}
    except (json.JSONDecodeError, TypeError):
        return {}

def _create_human_input_request(
    task_id: str,
    human_input_data: Dict[str, Any],
    db,
) -> Optional["HumanInputRequest"]:
    """
    创建人类输入请求记录。
    human_input_data 来自 _parse_agent_result 的返回值。
    """
    from datetime import datetime
    import uuid
    from models.human_input import HumanInputRequest

    try:
        human_input_request = HumanInputRequest(
            id=f"hir-{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            title=human_input_data.get("title", "Human Input Required"),
            description=human_input_data.get("description", ""),
            input_type=human_input_data.get("input_type", "confirmation"),
            status="pending",
            context=human_input_data.get("context", {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(human_input_request)
        db.commit()
        db.refresh(human_input_request)
        return human_input_request
    except Exception as e:
        logger.error(f"[ERROR] Failed to create human input request: {e}")
        db.rollback()
        return None

def _evaluate_scenario_evolution(db, scenario, success: bool) -> "ScenarioEvolutionResult":
    """
    MAK-228: 评估场景质量和自动升级。
    逻辑:
    1. 根据 success_rate 评估质量
       - > 80% → 高质量
       - 50-80% → 一般
       - < 50% → 需要改进
    2. 自动升级规则
       - 连续 5 次高质量执行 → status: draft → active
       - success_rate > 90% → 版本号 +0.1 (v1.0 → v1.1)
       - 连续 3 次失败 → status: active → deprecated (标记待审查)
    """
    from reins.api.tasks_models import ScenarioEvolutionResult

    result = ScenarioEvolutionResult(evaluated=True)

    try:
        # 获取执行历史
        exec_log_raw = scenario.execution_log
        if exec_log_raw and isinstance(exec_log_raw, str):
            try:
                exec_log = json.loads(exec_log_raw)
            except Exception:
                exec_log = []
        elif exec_log_raw and isinstance(exec_log_raw, list):
            exec_log = exec_log_raw
        else:
            exec_log = []

        recent_executions = []
        success_count = 0
        failure_count = 0

        for v in reversed(exec_log[-10:]):
            if isinstance(v, dict):
                status = v.get('status', '')
                success_flag = v.get('success', False)
                recent_executions.append({'status': status, 'success': success_flag})
                if success_flag:
                    success_count += 1
                else:
                    failure_count += 1

        success_rate = scenario.success_rate or 0

        # 评估场景质量
        if success_rate > 80:
            assessment = "high_quality"
        elif success_rate >= 50:
            assessment = "moderate"
        else:
            assessment = "needs_improvement"
        result.assessment = assessment

        # 自动版本升级: 成功率 > 90% → 版本号 +0.1
        if success_rate > 90:
            current_version = scenario.version or "v1.0"
            try:
                clean_version = current_version.lstrip('v')
                parts = clean_version.split('.')
                if len(parts) == 2:
                    major = int(parts[0])
                    minor = int(parts[1])
                    new_version = f"v{major}.{minor + 1}"
                    scenario.version = new_version
                    result.version_upgraded = True
                    result.new_version = new_version
                    result.reason = f"Success rate > 90%, version upgraded to {new_version}"
                else:
                    result.new_version = current_version
            except Exception as e:
                logger.warning(f"[MAK-228] Version parse warning: {e}")
                result.new_version = current_version

        # 状态迁移评估
        current_status = scenario.status or "draft"
        new_status = current_status
        status_changed = False
        reason = result.reason or ""

        # 高质量 + draft → active
        if assessment == "high_quality" and current_status == "draft":
            if success_count >= 5 and len(recent_executions) >= 5:
                new_status = "active"
                status_changed = True
                reason = reason + "; draft → active (5 consecutive high-quality executions)"

        # 失败率高 → deprecated
        if failure_count >= 3 and current_status == "active":
            new_status = "deprecated"
            status_changed = True
            reason = reason + "; active → deprecated (3 consecutive failures, needs review)"

        if status_changed:
            scenario.status = new_status
            result.status_changed = True
            result.new_status = new_status

        if not reason and result.version_upgraded:
            reason = f"Success rate {success_rate:.1f}% triggered version upgrade"
        result.reason = reason

    except Exception as e:
        logger.warning(f"[MAK-228] Scenario evolution evaluation warning: {e}")
        result.evaluated = False
        result.reason = f"Evaluation warning: {str(e)}"

    return result