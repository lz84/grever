"""Scenario Custom Create & DAG Build API"""
from loguru import logger
import uuid
import json
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from reins.common.database import get_db
from services.tag_prerequisites import (
    validate_prerequisites,
    check_deprecated_tags,
    resolve_all_prerequisites,
    CircularDependencyError,
)
from ..models.scenario import Scenario, ScenarioTask, CustomScenarioCreateRequest, CustomScenarioCreateResponse, TaskTemplateResponse

router = APIRouter(tags=["scenarios"])

def _parse_json_list(value):
    """Parse a JSON string or list to Python list"""
    if not value:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return value
    return []

def _get_condition(task) -> tuple:
    """从 task 对象获取 condition_type 和 condition_data"""
    condition_type = getattr(task, 'condition_type', None) or 'none'
    condition_data = getattr(task, 'condition_data', None) or {}
    return condition_type, condition_data

def _build_template_dag(all_templates: List[Dict[str, Any]], phases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """根据任务模板和阶段构建 template_dag"""
    nodes = []
    edges = []
    phase_map = {}
    for t in all_templates:
        if not isinstance(t, dict):
            logger.warning(f"[DAG] Skipping non-dict template: {t}")
            continue
        node_type = t.get('node_type', 'step')
        node = {
            "id": t.get('id', ''),
            "type": node_type,
            "name": t.get('name', ''),
            "properties": {
                "phase_name": t.get('phase_name', ''),
                "description": t.get('description', ''),
                "agent_type": t.get('agent_type', ''),
                "required_capabilities": t.get('required_capabilities', []),
                "condition_type": t.get('condition_type', 'none'),
                "condition_data": t.get('condition_data') or {},
            }
        }
        if node_type == 'parallel':
            node["properties"]["children"] = t.get('children', [])
        nodes.append(node)
    for phase in phases:
        phase_name = phase['phase_name']
        phase_map[phase_name] = []
        for task_id in phase.get('tasks', []):
            phase_map[phase_name].append(task_id)
    template_id_by_name = {t['name']: t['id'] for t in all_templates if isinstance(t, dict)}
    for t in all_templates:
        if not isinstance(t, dict):
            continue
        deps = t.get('dependencies') or []
        for dep_name in deps:
            if dep_name in template_id_by_name:
                edges.append([template_id_by_name[dep_name], t['id']])
    for phase in phases:
        phase_name = phase['phase_name']
        depends_on = phase.get('depends_on_phases') or []
        for dep_phase in depends_on:
            if dep_phase in phase_map:
                for from_id in phase_map[dep_phase]:
                    for to_id in phase_map[phase_name]:
                        if [from_id, to_id] not in edges:
                            edges.append([from_id, to_id])
    return {"nodes": nodes, "edges": edges, "phases": phase_map}

def _make_task_dict(template_id: str, scenario_id: str, phase_name: str,
                    task, order_in_phase: int) -> Dict[str, Any]:
    """构建 task 字典"""
    condition_type, condition_data = _get_condition(task)
    return {
        "id": template_id,
        "scenario_id": scenario_id,
        "phase_name": phase_name,
        "name": getattr(task, 'name', None) or '',
        "description": getattr(task, 'description', None),
        "agent_type": getattr(task, 'agent_type', None),
        "required_capabilities": getattr(task, 'required_capabilities', None) or [],
        "dependencies_raw": getattr(task, 'dependencies', None) or [],
        "order_in_phase": order_in_phase,
        "estimated_hours": getattr(task, 'estimated_hours', None) or 0.0,
        "priority": getattr(task, 'priority', None) or 'medium',
        "node_type": getattr(task, 'node_type', None) or 'step',
        "children": getattr(task, 'children', None) or [],
        "condition_type": condition_type,
        "condition_data": condition_data,
        "then_node": getattr(task, 'then_node', None) or '',
        "else_node": getattr(task, 'else_node', None) or '',
    }

def _collect_all_capabilities(temp_templates: List[Dict[str, Any]]) -> List[str]:
    """从所有任务模板中收集所有 required_capabilities（去重）"""
    cap_set = set()
    for t in temp_templates:
        if not isinstance(t, dict):
            continue
        caps = t.get('required_capabilities') or []
        if isinstance(caps, list):
            for c in caps:
                if c:
                    cap_set.add(c)
        elif isinstance(caps, str):
            try:
                parsed = json.loads(caps)
                if isinstance(parsed, list):
                    for c in parsed:
                        if c:
                            cap_set.add(c)
            except (json.JSONDecodeError, TypeError):
                pass
    return list(cap_set)

@router.post("/custom-create", response_model=None, status_code=201)
def custom_create_scenario(request: CustomScenarioCreateRequest, db: Session = Depends(get_db)):
    """自定义场景创建 API（三层结构）"""
    from datetime import datetime

    # Sprint 98 B98-5: 前置标签校验
    strict_mode = request.strict_mode if hasattr(request, 'strict_mode') else False

    try:
        basic = request.basic
        scenario = Scenario(
            id=f"scenario-{uuid.uuid4().hex[:12]}",
            name=basic.name,
            category=basic.category,
            status=basic.status or 'draft',
            version=basic.version or 'v1.0',
            description=basic.description,
            scenario_desc=basic.scenario_desc or "",
            triggers=basic.triggers or [],
            source=basic.source or 'manual',
            versions=[basic.version or 'v1.0'],
            template_dag={},
        )
        db.add(scenario)
        db.flush()

        workflow = request.project_workflow
        phases_data = []
        temp_templates = []

        # Process each phase
        for phase in workflow.phases:
            phase_info = {
                "phase_name": phase.phase_name,
                "phase_description": getattr(phase, 'phase_description', None),
                "depends_on_phases": getattr(phase, 'depends_on_phases', None) or [],
                "tasks": []
            }

            # Tasks within this phase
            for i, task in enumerate(phase.tasks):
                template_id = f"task-{uuid.uuid4().hex[:12]}"
                t = _make_task_dict(template_id, scenario.id, phase.phase_name, task, i)
                phase_info["tasks"].append(template_id)
                temp_templates.append(t)

            phases_data.append(phase_info)

        # DROPPED: scenario_steps table removed, no longer creating step records

        # Global tasks (not assigned to any phase)
        if request.task_templates:
            for j, task in enumerate(request.task_templates):
                template_id = f"task-{uuid.uuid4().hex[:12]}"
                t = _make_task_dict(template_id, scenario.id, "global", task, 2000 + j)
                temp_templates.append(t)

        # Resolve dependencies by name -> ID
        name_to_id = {t['name']: t['id'] for t in temp_templates if isinstance(t, dict) and t.get('name')}
        for t in temp_templates:
            if not isinstance(t, dict):
                continue
            raw_deps = t.get('dependencies_raw') or []
            t['dependencies'] = [name_to_id[d] for d in raw_deps if d in name_to_id]

        # Sprint 98 B98-5: 收集所有 capabilities 并校验
        all_caps = _collect_all_capabilities(temp_templates)
        if all_caps:
            # 1. 环形依赖检测
            try:
                validate_prerequisites(all_caps)
            except CircularDependencyError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "circular_dependency",
                        "message": str(e),
                        "type": "circular_dependency",
                    }
                )
            # 2. 缺失 prerequisites 校验
            missing = validate_prerequisites(all_caps)
            if missing:
                if strict_mode:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "missing_prerequisites",
                            "message": f"Missing prerequisites: {missing}",
                            "type": "missing_prerequisites",
                            "missing": missing,
                        }
                    )
                else:
                    # 非 strict 模式：自动补全
                    all_tags = resolve_all_prerequisites(all_caps)
                    auto_added = [t for t in all_tags if t not in all_caps]
                    # 将 auto_added 注入到所有任务的 required_capabilities
                    for t in temp_templates:
                        if isinstance(t, dict):
                            existing = t.get('required_capabilities') or []
                            for new_tag in auto_added:
                                if new_tag not in existing:
                                    existing.append(new_tag)
                            t['required_capabilities'] = existing
            # 3. deprecated 标签警告（不阻断，只记录到 response）
            deprecated_warnings = check_deprecated_tags(all_caps)

        # Build template_dag
        template_dag = _build_template_dag(temp_templates, phases_data)
        scenario.template_dag = template_dag

        # Write DB records
        task_template_responses = []
        for t in temp_templates:
            if not isinstance(t, dict):
                continue
            db_template = ScenarioTask(
                id=t['id'],
                scenario_id=t['scenario_id'],
                phase_name=t['phase_name'],
                name=t['name'],
                description=t.get('description'),
                agent_type=t.get('agent_type'),
                required_capabilities=t.get('required_capabilities') or [],
                dependencies=t.get('dependencies') or [],
                order_in_phase=t['order_in_phase'],
                estimated_hours=t.get('estimated_hours') or 0.0,
                priority=t.get('priority') or 'medium',
                condition_type=t.get('condition_type') or 'none',
                condition_data=json.dumps(t.get('condition_data') or {}) if t.get('condition_data') else None,
            )
            db.add(db_template)
            task_template_responses.append(TaskTemplateResponse(
                id=t['id'],
                scenario_id=t['scenario_id'],
                phase_name=t['phase_name'],
                name=t['name'],
                description=t.get('description'),
                agent_type=t.get('agent_type'),
                required_capabilities=t.get('required_capabilities') or [],
                dependencies=t.get('dependencies') or [],
                order_in_phase=t['order_in_phase'],
                estimated_hours=t.get('estimated_hours') or 0.0,
                priority=t.get('priority') or 'medium',
                condition_type=t.get('condition_type') or 'none',
                condition_data=json.dumps(t.get('condition_data') or {}) if t.get('condition_data') else None,
            ))

        db.commit()
        db.refresh(scenario)

        # 构建 warnings
        warnings = []
        auto_added_tags = []
        auto_added_reason = ""
        if all_caps and 'deprecated_warnings' in dir():
            for dw in deprecated_warnings:
                warnings.append({
                    "type": "deprecated_tag",
                    "tag_id": dw["tag_id"],
                    "message": f"Tag {dw['tag_id']} is deprecated. Consider replacing with {dw['replaced_by']}",
                    "replaced_by": dw["replaced_by"]
                })
        if not strict_mode and all_caps:
            try:
                validate_prerequisites(all_caps)
            except CircularDependencyError:
                pass
            else:
                missing = validate_prerequisites(all_caps)
                if not missing:
                    all_tags = resolve_all_prerequisites(all_caps)
                    auto_added = [t for t in all_tags if t not in all_caps]
                    if auto_added:
                        auto_added_tags = auto_added
                        auto_added_reason = f"auto-added {len(auto_added)} prerequisite tags"

        return CustomScenarioCreateResponse(
            id=scenario.id,
            name=scenario.name,
            category=scenario.category,
            status=scenario.status,
            version=scenario.version,
            description=scenario.description,
            scenario_desc=scenario.scenario_desc,
            template_dag=scenario.template_dag,
            phases=[{"phase_name": p["phase_name"], "depends_on_phases": p.get("depends_on_phases", []), "task_count": len(p.get("tasks", []))} for p in phases_data],
            task_templates=task_template_responses,
            created_at=scenario.created_at.isoformat() if scenario.created_at else None,
            updated_at=scenario.updated_at.isoformat() if scenario.updated_at else None,
            # Sprint 98 B98-5
            warnings=warnings if warnings else None,
            auto_added_tags=auto_added_tags if auto_added_tags else None,
            auto_added_reason=auto_added_reason if auto_added_reason else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[scenarios] custom_create_scenario error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"自定义场景创建失败: {str(e)}")

# === Feedback (merged from scenarios_feedback.py) ===
"""Scenario Feedback, Versions & Metrics API"""
from loguru import logger
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from reins.common.database import get_db
from ..models.scenario import Scenario, ScenarioMetrics, FeedbackRequest, FeedbackResponse

router = APIRouter(tags=["scenarios"])

@router.get("/{scenario_id}/versions", response_model=List[Dict[str, Any]])
def get_scenario_versions(scenario_id: str, db: Session = Depends(get_db)):
    """Sprint 22: 获取 Scenario 版本列表"""
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        versions_data = scenario.versions or []
        if isinstance(versions_data, str):
            try:
                import json as json_module
                versions_data = json_module.loads(versions_data)
            except:
                versions_data = []
        return [
            {
                "id": f"{scenario_id}-v{i+1}",
                "scenario_id": scenario_id,
                "version": v,
                "name": f"{scenario.name} v{v}",
                "status": "active",
                "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
            }
            for i, v in enumerate(versions_data)
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询场景版本失败: {str(e)}")

@router.post("/{scenario_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(scenario_id: str, feedback: FeedbackRequest, db: Session = Depends(get_db)):
    """提交场景反馈（执行完成后调用）"""
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        scenario.total_executions = (scenario.total_executions or 0) + 1
        if feedback.status == 'completed':
            scenario.success_count = (scenario.success_count or 0) + 1
        else:
            scenario.failed_count = (scenario.failed_count or 0) + 1
        new_duration = feedback.duration_ms or 0
        if scenario.avg_duration_ms and scenario.total_executions > 1:
            scenario.avg_duration_ms = (
                (scenario.avg_duration_ms * (scenario.total_executions - 1) + new_duration) / scenario.total_executions
            )
        else:
            scenario.avg_duration_ms = new_duration
        scenario.success_rate = (
            (scenario.success_count / scenario.total_executions * 100) if scenario.total_executions > 0 else 0
        )
        scenario.usage_count = (scenario.usage_count or 0) + 1
        new_version_suggested = False
        if feedback.user_modifications and len(feedback.user_modifications) >= 3:
            new_version_suggested = True
            current_version = scenario.version or "v1.0"
            parts = current_version.lstrip('v').split('.')
            if len(parts) == 2:
                major, minor = int(parts[0]), int(parts[1])
                minor += 1
                new_version = f"v{major}.{minor}"
            else:
                new_version = "v1.1"
            scenario.version = new_version
            if scenario.versions is None:
                scenario.versions = []
            elif isinstance(scenario.versions, str):
                import json
                try:
                    scenario.versions = json.loads(scenario.versions)
                except:
                    scenario.versions = []
            version_record = {
                "version": new_version,
                "modified_at": datetime.utcnow().isoformat(),
                "modifications_count": len(feedback.user_modifications),
                "modifications": feedback.user_modifications
            }
            scenario.versions.append(version_record)
        scenario.updated_at = datetime.utcnow()
        db.commit()
        return FeedbackResponse(
            success=True,
            new_version_suggested=new_version_suggested,
            updated_metrics=ScenarioMetrics(
                total_executions=scenario.total_executions or 0,
                success_count=scenario.success_count or 0,
                failed_count=scenario.failed_count or 0,
                avg_duration_ms=scenario.avg_duration_ms or 0,
                min_duration_ms=scenario.min_duration_ms or 0,
                max_duration_ms=scenario.max_duration_ms or 0,
                avg_conflicts=scenario.avg_conflicts or 0,
                avg_step_completion=scenario.avg_step_completion or 0,
            ),
            message="Feedback recorded successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[scenarios] submit_feedback error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")
