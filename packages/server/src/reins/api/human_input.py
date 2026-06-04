"""
人类输入 API 端点（Facade）

Endpoints:
- GET  /api/v1/human-input/pending        - 查询所有待处理请求
- GET  /api/v1/human-input/{input_id}     - 获取详情
- POST /api/v1/human-input/{input_id}/submit - 提交输入
- POST /api/v1/human-input/{input_id}/reject - 拒绝
- GET  /api/v1/human-input/task/{task_id} - 查询任务相关请求
- GET  /api/v1/human-input/recent          - 最近请求
- GET  /api/v1/human-input/stats           - 统计数据
- GET  /api/v1/human-input/review-stats    - 人类审核统计

Created for T5: API endpoints - request/submit/reject/pending query

模块拆分:
- human_input_models.py   : Pydantic 模型 + 辅助函数
- human_input_queries.py   : 只读查询端点
- human_input_actions.py  : 写操作端点
- human_input_stats.py    : 统计端点
"""
from fastapi import APIRouter

from reins.api.human_input_models import (
    HumanInputRequest,
    CreateHumanInputRequest,
    SubmitHumanInputRequest,
    HumanInputResponse,
    PendingHumanInputResponse,
    HumanReviewStats,
    create_human_input_request,
)
from reins.api.human_input_queries import router as queries_router
from reins.api.human_input_actions import router as actions_router
from reins.api.human_input_stats import router as stats_router

# 合并所有子模块路由
router = APIRouter(prefix="/api/v1/human-input", tags=["human-input"])

# Merge routers: literal routes first (stats), then parameterized (queries)
router.include_router(stats_router)
router.include_router(queries_router)
router.include_router(actions_router)

__all__ = [
    "router",
    # 暴露常用模型供外部导入
    "HumanInputRequest",
    "CreateHumanInputRequest",
    "SubmitHumanInputRequest",
    "HumanInputResponse",
    "PendingHumanInputResponse",
    "HumanReviewStats",
    "create_human_input_request",
]
