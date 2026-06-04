"""负载管理 API - Facade（合并子模块路由，导出离线处理函数）"""

from fastapi import APIRouter

from .load_manager_routes import router as _lm_router
from .load_manager_helpers import (
    check_and_mark_agents_offline,
    reassign_tasks_for_offline_agent,
    reassign_all_offline_agent_tasks,
    get_agent_load_info,
    check_agent_online,
    get_pending_tasks_count,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
router.include_router(_lm_router)
