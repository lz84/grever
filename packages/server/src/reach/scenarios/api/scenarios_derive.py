"""Scenario Derive from Execution & Cognitions API"""
from loguru import logger
import uuid
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db, get_db_manager
from ..models.scenario import Scenario, ScenarioTaskTemplate

router = APIRouter(tags=["scenarios"])

def _get_db_engine():
    return get_db_manager().engine

def _execute_raw_query(query: str, params: Dict[str, Any] = None):
    engine = _get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return result.fetchall()

def _build_template_dag(all_templates: List[Dict[str, Any]], phases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """根据任务模板和阶段构建 template_dag"""
    nodes = []
    edges = []
    phase_map = {}
    for t in all_templates:
        node_type = t.get('node_type', 'step')
        node = {
            "id": t['id'], "type": node_type, "name": t.get('task_name', ''),
            "properties": {
                "phase_name": t.get('phase_name', ''),
                "task_description": t.get('task_description', ''),
                "agent_type": t.get('agent_type', ''),
                "required_capabilities": t.get('required_capabilities', []),
            }
        }
        if node_type == 'parallel':
            node["properties"]["children"] = t.get('children', [])
        elif node_type == 'conditional':
            node["properties"]["condition"] = t.get('condition', '')
            node["properties"]["then_node"] = t.get('then_node', '')
            node["properties"]["else_node"] = t.get('else_node', '')
        nodes.append(node)
    for phase in phases:
        phase_name = phase['phase_name']
        phase_map[phase_name] = []
        for t in phase.get('tasks', []):
            phase_map[phase_name].append(t['id'])
    template_id_by_name = {t['task_name']: t['id'] for t in all_templates}
    for t in all_templates:
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

# ========== Task 3: 从目标提炼场景 API ==========

@router.post("/from-execution/{goal_id}", status_code=201)
def create_scenario_from_execution(goal_id: str, confirm: bool = Query(True), db: Session = Depends(get_db)):
    """
    Task 3: 从目标提炼场景 API
    POST /api/v1/scenarios/from-execution/{goal_id}
    """
    from ..models.goal import Goal
    from ..models.project import Project
    from ..models.task import Task
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
        projects = db.query(Project).filter(Project.goal_id == goal_id).all()
        project_ids = [p.id for p in projects]
        tasks = db.query(Task).filter(Task.project_id.in_(project_ids)).all() if project_ids else []
        phases_data = []
        all_templates = []
        name_to_id = {}
        project_tasks_map = {}
        for task in tasks:
            pid = task.project_id or 'default'
            if pid not in project_tasks_map:
                project_tasks_map[pid] = []
            project_tasks_map[pid].append(task)
        for project in projects:
            phase_name = project.name or f"phase-{project.id[:8]}"
            phase_tasks = project_tasks_map.get(project.id, [])
            tasks_data = []
            for i, task in enumerate(phase_tasks):
                template_id = f"template-{uuid.uuid4().hex[:12]}"
                task_dict = {
                    "id": template_id, "phase_name": phase_name,
                    "task_name": task.title, "task_description": task.description,
                    "agent_type": task.assigned_agent, "required_capabilities": [],
                    "dependencies": [], "dependencies_raw": [],
                    "order_in_phase": i, "estimated_hours": 0.0,
                    "priority": task.priority or 'medium', "status": task.status,
                }
                if hasattr(task, 'dependencies') and task.dependencies:
                    task_dict["dependencies_raw"] = [d.dependency_id for d in task.dependencies]
                elif hasattr(task, 'dependency_ids') and task.dependency_ids:
                    task_dict["dependencies_raw"] = task.dependency_ids
                tasks_data.append(task_dict)
                all_templates.append(task_dict)
                name_to_id[task.title] = template_id
            phases_data.append({
                "phase_name": phase_name, "phase_description": project.description,
                "depends_on_phases": [], "tasks": tasks_data,
                "project_id": project.id, "workflow_id": project.workflow_id,
            })
        default_tasks = project_tasks_map.get('default', [])
        if default_tasks:
            for i, task in enumerate(default_tasks):
                template_id = f"template-{uuid.uuid4().hex[:12]}"
                task_dict = {
                    "id": template_id, "phase_name": "default",
                    "task_name": task.title, "task_description": task.description,
                    "agent_type": task.assigned_agent, "required_capabilities": [],
                    "dependencies": [], "dependencies_raw": [],
                    "order_in_phase": i, "estimated_hours": 0.0,
                    "priority": task.priority or 'medium',
                }
                all_templates.append(task_dict)
                name_to_id[task.title] = template_id
            phases_data.append({
                "phase_name": "default", "phase_description": None,
                "depends_on_phases": [],
                "tasks": [t for t in all_templates if t['phase_name'] == 'default'],
            })
        task_id_to_title = {t.id: t.title for t in tasks}
        for t in all_templates:
            deps = t.get("dependencies_raw") or []
            resolved_deps = []
            for dep_id in deps:
                dep_title = task_id_to_title.get(str(dep_id))
                if dep_title and dep_title in name_to_id:
                    resolved_deps.append(name_to_id[dep_title])
            t["dependencies"] = resolved_deps
        template_dag = _build_template_dag(all_templates, phases_data)
        scenario = Scenario(
            id=f"scenario-{uuid.uuid4().hex[:12]}",
            name=f"{goal.title} - 执行提炼场景", category="general",
            status="draft", version="v1.0",
            description=goal.description,
            scenario_desc=f"从目标 {goal_id} 的执行记录提炼的场景",
            triggers=[], source="execution_derived",
            template_dag=template_dag, versions=["v1.0"],
        )
        db.add(scenario)
        db.flush()
        for t in all_templates:
            db_template = ScenarioTaskTemplate(
                id=t['id'], scenario_id=scenario.id, phase_name=t['phase_name'],
                task_name=t['task_name'], task_description=t['task_description'],
                agent_type=t['agent_type'], required_capabilities=t['required_capabilities'],
                dependencies=t['dependencies'], order_in_phase=t['order_in_phase'],
                estimated_hours=t['estimated_hours'], priority=t['priority'],
            )
            db.add(db_template)
        db.commit()
        db.refresh(scenario)
        return {
            "id": scenario.id, "name": scenario.name, "category": scenario.category,
            "status": scenario.status, "version": scenario.version,
            "description": scenario.description, "scenario_desc": scenario.scenario_desc,
            "source": scenario.source, "template_dag": scenario.template_dag,
            "goal_id": goal_id, "projects_count": len(projects), "tasks_count": len(tasks),
            "phases": [{"phase_name": p["phase_name"], "phase_description": p.get("phase_description"), "task_count": len(p.get("tasks", [])), "project_id": p.get("project_id")} for p in phases_data],
            "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
            "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[scenarios] create_scenario_from_execution error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"从目标提炼场景失败: {str(e)}")

# ========== Task 4: 从项目提炼场景 API ==========

@router.post("/from-execution/project/{project_id}", status_code=201)
def create_scenario_from_project(project_id: str, confirm: bool = Query(True), db: Session = Depends(get_db)):
    """
    Task 4: 从项目提炼场景 API
    POST /api/v1/scenarios/from-execution/project/{project_id}
    """
    from ..models.project import Project
    from ..models.task import Task
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        all_templates = []
        name_to_id = {}
        task_id_to_title = {}
        phase_name = project.name or f"phase-{project_id[:8]}"
        for i, task in enumerate(tasks):
            template_id = f"template-{uuid.uuid4().hex[:12]}"
            task_dict = {
                "id": template_id, "phase_name": phase_name,
                "task_name": task.title, "task_description": task.description,
                "agent_type": task.assigned_agent, "required_capabilities": [],
                "dependencies": [], "dependencies_raw": [],
                "order_in_phase": i, "estimated_hours": 0.0,
                "priority": task.priority or 'medium',
            }
            if hasattr(task, 'dependencies') and task.dependencies:
                task_dict["dependencies_raw"] = [str(d.dependency_id) for d in task.dependencies]
            elif hasattr(task, 'dependency_ids') and task.dependency_ids:
                task_dict["dependencies_raw"] = [str(d) for d in task.dependency_ids]
            all_templates.append(task_dict)
            name_to_id[task.title] = template_id
            task_id_to_title[str(task.id)] = task.title
        for t in all_templates:
            deps = t.get("dependencies_raw") or []
            resolved_deps = []
            for dep_id in deps:
                dep_title = task_id_to_title.get(dep_id)
                if dep_title and dep_title in name_to_id:
                    resolved_deps.append(name_to_id[dep_title])
            t["dependencies"] = resolved_deps
        phases_data = [{
            "phase_name": phase_name, "phase_description": project.description,
            "depends_on_phases": [], "tasks": all_templates,
            "project_id": project_id, "workflow_id": project.workflow_id,
        }]
        template_dag = _build_template_dag(all_templates, phases_data)
        scenario = Scenario(
            id=f"scenario-{uuid.uuid4().hex[:12]}",
            name=f"{project.name} - 执行提炼场景", category="general",
            status="draft", version="v1.0",
            description=project.description,
            scenario_desc=f"从项目 {project_id} 的执行记录提炼的场景",
            triggers=[], source="execution_derived",
            template_dag=template_dag, versions=["v1.0"],
        )
        db.add(scenario)
        db.flush()
        for t in all_templates:
            db_template = ScenarioTaskTemplate(
                id=t['id'], scenario_id=scenario.id, phase_name=t['phase_name'],
                task_name=t['task_name'], task_description=t['task_description'],
                agent_type=t['agent_type'], required_capabilities=t['required_capabilities'],
                dependencies=t['dependencies'], order_in_phase=t['order_in_phase'],
                estimated_hours=t['estimated_hours'], priority=t['priority'],
            )
            db.add(db_template)
        db.commit()
        db.refresh(scenario)
        return {
            "id": scenario.id, "name": scenario.name, "category": scenario.category,
            "status": scenario.status, "version": scenario.version,
            "description": scenario.description, "scenario_desc": scenario.scenario_desc,
            "source": scenario.source, "template_dag": scenario.template_dag,
            "project_id": project_id, "tasks_count": len(tasks),
            "phases": [{"phase_name": phase_name, "phase_description": project.description, "task_count": len(all_templates), "workflow_id": project.workflow_id}],
            "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
            "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[scenarios] create_scenario_from_project error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"从项目提炼场景失败: {str(e)}")

# === Cognitions (merged from scenarios_cognitions.py) ===
"""Scenario Cognition Derivation API"""
from loguru import logger
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db, get_db_manager

router = APIRouter(tags=["scenarios"])

def _get_db_engine():
    return get_db_manager().engine

def get_cognitions_by_domain(domain: str) -> List[Dict]:
    """按领域读取认知 - 内部函数，不暴露为API"""
    engine = _get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, type, domain, content, tags, confidence, source, created_at, updated_at
            FROM cognitions
            WHERE domain = :domain
        """), {"domain": domain})
        rows = result.fetchall()
        return [
            {
                "id": row[0], "type": row[1], "domain": row[2], "content": row[3],
                "tags": row[4], "confidence": row[5], "source": row[6],
                "created_at": row[7], "updated_at": row[8]
            }
            for row in rows
        ]

def get_cognitions_by_ids(ids: List[int]) -> List[Dict]:
    """按ID读取认知 - 内部函数，不暴露为API"""
    if not ids:
        return []
    params = {f'id_{i}': id_val for i, id_val in enumerate(ids)}
    placeholders = ','.join([f':id_{i}' for i in range(len(ids))])
    engine = _get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT id, type, domain, content, tags, confidence, source, created_at, updated_at
            FROM cognitions
            WHERE id IN ({placeholders})
        """), params)
        rows = result.fetchall()
        return [
            {
                "id": row[0], "type": row[1], "domain": row[2], "content": row[3],
                "tags": row[4], "confidence": row[5], "source": row[6],
                "created_at": row[7], "updated_at": row[8]
            }
            for row in rows
        ]

# ========== Task 6: 认知→场景 LLM 管道 API ==========

@router.post("/derive-from-cognitions")
def derive_scenario_from_cognitions(request: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    从认知生成场景预览
    POST /api/v1/scenarios/derive-from-cognitions
    """
    try:
        domain = request.get("domain")
        cognition_ids = request.get("cognition_ids", [])
        goal_title = request.get("goal_title", "")
        if not domain:
            raise HTTPException(status_code=400, detail="缺少 domain 参数")
        cognitions = get_cognitions_by_ids(cognition_ids)
        if not cognitions:
            cognitions = get_cognitions_by_domain(domain)
        if not cognitions:
            raise HTTPException(status_code=404, detail=f"未找到领域 '{domain}' 的认知数据")
        cognition_contents = "\n".join([f"- {c['type']}: {c['content']}" for c in cognitions])
        prompt = f"""
        基于以下认知知识，生成一个应急场景：
        认知内容：{cognition_contents}
        领域：{domain}
        请生成一个结构化的场景JSON...
        """
        # 模拟生成场景（实际调用LLM需要API密钥）
        scenario_preview = {
            "name": goal_title or f"{domain}应急场景",
            "category": domain,
            "description": f"基于{len(cognitions)}条认知生成的{domain}应急场景",
            "scenario_desc": f"这是一个基于认知库中关于{domain}领域专业知识生成的应急场景。",
            "triggers": ["应急事件发生", "风险阈值触发", "外部告警信号"],
            "steps": [
                {"order": 1, "name": "风险评估", "agent_type": "分析代理", "required_capabilities": ["数据分析", "风险评估"]},
                {"order": 2, "name": "资源调度", "agent_type": "调度代理", "required_capabilities": ["资源管理", "调度优化"]},
                {"order": 3, "name": "决策执行", "agent_type": "决策代理", "required_capabilities": ["决策制定", "执行监控"]},
            ],
            "agent_requirements": {
                "required_types": ["分析代理", "调度代理", "决策代理"],
                "recommended_skills": ["应急响应", "风险评估", "资源调配"],
            },
            "template_dag": {
                "nodes": [
                    {"id": "risk_analysis", "type": "step", "name": "风险评估", "properties": {"phase_name": "评估阶段", "task_description": "进行风险评估和分析", "agent_type": "分析代理", "required_capabilities": ["数据分析", "风险评估"]}},
                    {"id": "resource_allocation", "type": "parallel", "name": "资源分配", "properties": {"phase_name": "调度阶段", "task_description": "并行分配各种资源", "agent_type": "调度代理", "required_capabilities": ["资源管理", "调度优化"], "children": ["allocate_equipment", "allocate_personnel", "allocate_funds"]}},
                    {"id": "allocate_equipment", "type": "step", "name": "设备分配", "properties": {"phase_name": "调度阶段", "task_description": "分配所需设备", "agent_type": "调度代理", "required_capabilities": ["设备管理"]}},
                    {"id": "allocate_personnel", "type": "step", "name": "人员分配", "properties": {"phase_name": "调度阶段", "task_description": "分配所需人员", "agent_type": "调度代理", "required_capabilities": ["人员管理"]}},
                    {"id": "allocate_funds", "type": "step", "name": "资金分配", "properties": {"phase_name": "调度阶段", "task_description": "分配所需资金", "agent_type": "财务代理", "required_capabilities": ["财务管理"]}},
                    {"id": "decision_making", "type": "conditional", "name": "决策制定", "properties": {"phase_name": "执行阶段", "task_description": "根据情况制定决策", "agent_type": "决策代理", "required_capabilities": ["决策制定", "执行监控"], "condition": "risk_level > 5", "then_node": "emergency_response", "else_node": "standard_procedure"}},
                    {"id": "emergency_response", "type": "step", "name": "应急响应", "properties": {"phase_name": "执行阶段", "task_description": "执行紧急响应程序", "agent_type": "应急代理", "required_capabilities": ["应急响应"]}},
                    {"id": "standard_procedure", "type": "step", "name": "标准程序", "properties": {"phase_name": "执行阶段", "task_description": "执行标准处理程序", "agent_type": "常规代理", "required_capabilities": ["常规处理"]}},
                ],
                "edges": [
                    ["risk_analysis", "resource_allocation"],
                    ["resource_allocation", "allocate_equipment"],
                    ["resource_allocation", "allocate_personnel"],
                    ["resource_allocation", "allocate_funds"],
                    ["allocate_equipment", "decision_making"],
                    ["allocate_personnel", "decision_making"],
                    ["allocate_funds", "decision_making"],
                    ["decision_making", "emergency_response"],
                    ["decision_making", "standard_procedure"],
                ],
                "phases": {"评估阶段": ["risk_analysis"], "调度阶段": ["resource_allocation", "allocate_equipment", "allocate_personnel", "allocate_funds"], "执行阶段": ["decision_making", "emergency_response", "standard_procedure"]},
            }
        }
        scenario_preview["derived_from_cognition_ids"] = cognition_ids
        return scenario_preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成场景失败: {str(e)}")

@router.post("/derive-from-cognitions/confirm", status_code=201)
def confirm_derived_scenario(scenario_data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    确认生成的场景并保存到数据库
    POST /api/v1/scenarios/derive-from-cognitions/confirm
    """
    from datetime import datetime
    import json
    import uuid as uuid_lib
    from ..models.scenario import Scenario, ScenarioTaskTemplate
    try:
        scenario_name = scenario_data.get("name", "未知场景")
        scenario_category = scenario_data.get("category", "general")
        scenario_description = scenario_data.get("description", "")
        scenario_desc = scenario_data.get("scenario_desc", "")
        triggers = scenario_data.get("triggers", [])
        steps = scenario_data.get("steps", [])
        agent_requirements = scenario_data.get("agent_requirements", {})
        template_dag = scenario_data.get("template_dag", {})
        scenario_id = f"scenario-{uuid_lib.uuid4().hex[:12]}"
        scenario = Scenario(
            id=scenario_id,
            name=scenario_name, category=scenario_category,
            status="active", version="v1.0",
            description=scenario_description, scenario_desc=scenario_desc,
            triggers=triggers, source="cognition_derived",
            template_dag=template_dag, versions=["v1.0"],
        )
        db.add(scenario)
        db.flush()
        task_templates_data = scenario_data.get("task_templates", [])
        for i, template_data in enumerate(task_templates_data):
            template_id = f"template-{uuid_lib.uuid4().hex[:12]}"
            task_template = ScenarioTaskTemplate(
                id=template_id, scenario_id=scenario.id,
                phase_name=template_data.get("phase_name", f"Phase_{i+1}"),
                task_name=template_data.get("task_name", f"Task_{i+1}"),
                task_description=template_data.get("task_description", ""),
                agent_type=template_data.get("agent_type", ""),
                required_capabilities=template_data.get("required_capabilities", []),
                dependencies=template_data.get("dependencies", []),
                order_in_phase=template_data.get("order_in_phase", i),
                estimated_hours=template_data.get("estimated_hours", 0.0),
                priority=template_data.get("priority", "medium"),
            )
            db.add(task_template)
        cognition_ids = scenario_data.get("derived_from_cognition_ids", [])
        for cognition_id in cognition_ids:
            association_id = f"assoc-{uuid_lib.uuid4().hex[:12]}"
            db.execute(text("""
                INSERT INTO scenario_cognitions (id, scenario_id, cognition_id, relevance_score, created_at)
                VALUES (:id, :scenario_id, :cognition_id, :relevance_score, datetime('now'))
            """), {"id": association_id, "scenario_id": scenario.id, "cognition_id": cognition_id, "relevance_score": 0.8})
        db.commit()
        db.refresh(scenario)
        return {"id": scenario.id, "name": scenario.name, "category": scenario.category, "status": scenario.status, "message": "场景已成功创建并关联认知"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"确认场景失败: {str(e)}")
