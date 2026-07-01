"""路由注册表 — 从 server.py 拆分（server.py ≤ 50 行铁律）"""

from reins.api.agents_router import router as agents_router
from reins.api.agent_platforms_router import router as agent_platforms_router
from api.traces_router import router as traces_router
from reins.api.scheduler_router import router as scheduler_router, internal_router
from reach.search.api.search_router import router as search_router
from vigil.api.security_endpoints_router import router as security_router
from reins.api.workflows import router as workflows_router
from reins.api.goals_exploration_mode import router as goals_exploration_mode_router
from reins.api.goals_exploration_lifecycle import router as goals_exploration_lifecycle_router
from reins.api.goals_research_iteration import router as goals_exploration_iteration_router
from reins.api.tasks import router as tasks_router
from reins.api.tasks_human_input import router as tasks_hitl_router
from reins.api.goals import router as goals_router
from reach.scenarios.api.scenarios_crud import router as scenarios_router
from reach.scenarios.api.scenarios_custom import router as scenarios_custom_router
from reins.api.projects import router as projects_router
from reach.artifacts.api.artifacts import router as artifacts_router
from api.reports import router as reports_router
from reins.api.human_review import router as human_review_router
from reins.api.assignment import router as assignment_router
from reins.api.goal_decompose import router as goal_decompose_router
from reins.api.human_input import router as human_input_router
from evo.api.dispute_manage import router as dispute_router
from evo.api.capsule_routes import router as capsule_router
from api.settings import router as settings_router
from reins.api.workflow_edit import router as workflow_edit_router
from grasp.api.knowledge_injector import router as knowledge_injector_router
from grasp.api.inject import router as inject_router
from grasp.api.grasp_routes import router as grasp_facade_router
from grasp.api.grasp_cognition import router as grasp_cognition_router
from grasp.api.grasp_knowledge import router as grasp_knowledge_router
from grasp.api.grasp_assessment import router as grasp_assessment_router
from reach.mcp.api.mcp import router as mcp_router
from reins.api.task_features import router as task_features_router
from reach.capabilities import router as capabilities_router
from api.dag_conversation import router as dag_router
from grasp.api.solutions import router as solutions_router
from api.api_documentation import router as api_doc_router
from reach.scenarios.api.scenario_instantiate import router as scenario_instantiate_router
from reach.skills import router as skills_router
from reach.skills_db_routes import router as skills_db_router
from reins.api.dashboard_stats import router as dashboard_stats_router
from reach.industry.api.industry_tags_routes import router as industry_tags_router
from reach.industry.api.industry_packs_routes import router as industry_packs_router
from reins.api.industry_pack_import import router as industry_pack_import_router
from reins.api.industry_pack_versions_routes import router as industry_pack_versions_router
from reins.api.industry_pack_validate import router as industry_pack_validate_router
from reins.api.industry_pack_export import router as industry_pack_export_router
from reach.knowledge import router as knowledge_router
from reach.agent_schemes.api import router as agent_schemes_router
from reach.attachments.api.attachments_router import router as attachments_router
from evo.api.genes_routes import router as genes_router
from evo.api.distillation_routes import router as distillation_router
from evo.api.evolution_events_routes import router as evolution_events_router
from evo.api.a2a_routes import router as a2a_router
from vigil.api.trust_routes import router as trust_router
from vigil.api.roles_routes import router as roles_router
from reins.api.agent_task_operations import router as agent_task_router
from reins.api.executions import router as executions_router


def get_routers() -> list:
    """返回所有路由配置（含 dict 格式的 prefix/tags 注册）"""
    return [
        agents_router, agent_platforms_router, traces_router, scheduler_router, internal_router,
        search_router, security_router, workflows_router, goals_exploration_mode_router, goals_exploration_lifecycle_router, goals_exploration_iteration_router,
        tasks_router, tasks_hitl_router, goals_router, scenarios_router, projects_router,
        artifacts_router, reports_router, human_review_router,
        assignment_router, goal_decompose_router, human_input_router,
        dispute_router, capsule_router, settings_router, workflow_edit_router,
        knowledge_injector_router, inject_router, grasp_facade_router,
        {"router": grasp_cognition_router, "prefix": "/api/v1/grasp", "tags": ["grasp-cognition"]},
        {"router": grasp_knowledge_router, "prefix": "/api/v1/grasp", "tags": ["grasp-knowledge"]},
        {"router": grasp_assessment_router, "prefix": "/api/v1/grasp", "tags": ["grasp-assessment"]},
        mcp_router, task_features_router, capabilities_router,
        dag_router, solutions_router, api_doc_router,
        {"router": scenarios_custom_router, "prefix": "/api/v1/scenarios", "tags": ["scenarios"]},
        scenario_instantiate_router, attachments_router,
        skills_router, skills_db_router, dashboard_stats_router,
        industry_tags_router,
        industry_pack_import_router, industry_pack_versions_router,
        industry_pack_validate_router, industry_pack_export_router,
        industry_packs_router,
        knowledge_router, agent_schemes_router,
        genes_router, distillation_router, evolution_events_router, a2a_router,
        trust_router, roles_router, agent_task_router, executions_router,
    ]
