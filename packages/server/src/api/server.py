"""FastAPI 应用入口（2026-05-14 Sprint 78/79 修复版）"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

src_path = Path(__file__).resolve().parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from reins.common import ReinsServer
from persistence.database import DatabaseManager
from persistence.base import DatabaseConfig
from reins.common.database import get_db
from api.app_state import set_reins, set_db_manager, setup_cors
from api.lifespan import lifespan_handler
from api.error_handler import register_exception_handlers

# Sprint 78 新路由（短文件）
from reins.api.agents_router import router as agents_router
from reins.api.agent_platforms_router import router as agent_platforms_router
from api.traces_router import router as traces_router
from reins.api.scheduler_router import router as scheduler_router, internal_router
from reach.search.api.search_router import router as search_router
from vigil.api.security_endpoints_router import router as security_router
from reins.api.workflows import router as workflows_router

# goals_exploration 子路由（facade 聚合）
from reins.api.goals_exploration import router as goals_exploration_router

# 遗留路由（facade 或 原文件）
from reins.api.tasks import router as tasks_router
from reins.api.tasks_human_input import router as tasks_hitl_router
from reins.api.goals import router as goals_router
from reach.scenarios.api.scenarios_crud import router as scenarios_router
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
from grasp.api.grasp_routes import router as grasp_facade_router
# GrASP cognition CRUD + knowledge/graph (代码已存在但未注册)
from grasp.api.grasp_cognition import router as grasp_cognition_router
from grasp.api.grasp_knowledge import router as grasp_knowledge_router
from reach.mcp.api.mcp import router as mcp_router
from reins.api.task_features import router as task_features_router
from reach.capabilities import router as capabilities_router
from api.dag_conversation import router as dag_router
from grasp.api.solutions import router as solutions_router
from api.api_documentation import router as api_doc_router
from reach.scenarios.api.scenario_instantiate import router as scenario_instantiate_router
from reach.skills import router as skills_router

# Sprint 93: 行业能力标签库
from reach.industry.api.industry_tags_routes import router as industry_tags_router
from reach.industry.api.industry_packs_routes import router as industry_packs_router

# Sprint 36: 项目级 Workflow (task-tree/diagram)

# Sprint 84: 附件路由
from reach.attachments.api.attachments_router import router as attachments_router

# Phase 2.2: 新补代码模块
from evo.api.genes_routes import router as genes_router
from evo.api.distillation_routes import router as distillation_router
from evo.api.evolution_events_routes import router as evolution_events_router
from evo.api.a2a_routes import router as a2a_router
# 注: scheduler tick 已由 scheduler_router 提供，无需额外文件
from vigil.api.trust_routes import router as trust_router
from vigil.api.roles_routes import router as roles_router
from reins.api.agent_task_operations import router as agent_task_router

def create_app() -> FastAPI:
    # 正确的 Nexus DB 路径：server.py 在 src/api/，DB 在项目根目录的 data/ 下
    db_path = os.environ.get("SQLITE_PATH") or str(Path(__file__).resolve().parents[4] / "data" / "reins.db")
    db_config = DatabaseConfig(provider="sqlite", path=db_path)
    reins = ReinsServer(db_config=db_config)
    db_manager = DatabaseManager(db_config)
    set_reins(reins)
    set_db_manager(db_manager)

    app = FastAPI(lifespan=lifespan_handler)
    setup_cors(app)

    # 注册所有路由
    for r in [
        agents_router, agent_platforms_router, traces_router, scheduler_router, internal_router,
        search_router, security_router, workflows_router,
        goals_exploration_router,
        tasks_router, tasks_hitl_router, goals_router, scenarios_router, projects_router,
        artifacts_router, reports_router, human_review_router,
        assignment_router, goal_decompose_router, human_input_router,
        dispute_router, capsule_router, settings_router, workflow_edit_router,
        knowledge_injector_router, grasp_facade_router,
        # GrASP cognition CRUD + knowledge/graph (prefix=/api/v1/grasp)
        {
            "router": grasp_cognition_router,
            "prefix": "/api/v1/grasp",
            "tags": ["grasp-cognition"],
        },
        {
            "router": grasp_knowledge_router,
            "prefix": "/api/v1/grasp",
            "tags": ["grasp-knowledge"],
        },
        mcp_router, task_features_router, capabilities_router,
        dag_router, solutions_router, api_doc_router,
        scenario_instantiate_router, attachments_router,
        skills_router,
        industry_tags_router,
        industry_packs_router,
        # Phase 2.2: 新补代码模块
        genes_router, distillation_router, evolution_events_router, a2a_router,
        trust_router, roles_router, agent_task_router,
    ]:
        if isinstance(r, dict):
            app.include_router(r["router"], prefix=r.get("prefix", ""), tags=r.get("tags", []))
        else:
            app.include_router(r)

    register_exception_handlers(app)
    return app

app = create_app()
