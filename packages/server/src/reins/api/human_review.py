"""人工裁决中心 API（Facade）

Endpoints:
- GET  /api/v1/human-review/stats          — 统计概览（Dashboard + 铃铛用）
- GET  /api/v1/human-review/pending        — 待处理列表（合并查询三种类型，分页筛选）
- POST /api/v1/human-review/batch-ruling   — 批量裁决（支持 disputed / waiting_human / assist 混合操作）
"""
from fastapi import APIRouter

from .human_review_stats import router as stats_router
from .human_review_batch import router as batch_router

router = APIRouter(prefix="/api/v1/human-review", tags=["human-review"])

router.include_router(stats_router)
router.include_router(batch_router)
