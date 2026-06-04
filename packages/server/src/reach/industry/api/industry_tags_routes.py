"""Industry Capability Tags CRUD API — Facade (split into sub-modules)

Sub-modules:
  - industry_tags_helpers:  shared utilities
  - industry_tags_list:     industry listing, agent tag endpoints, stats
  - industry_tags_crud:     tag CRUD + references
"""
from fastapi import APIRouter
from .industry_tags_list import router as list_router
from .industry_tags_crud import router as crud_router

router = APIRouter()
# Include list router first (has _industries, _stats, _by-industry, agent-tag-recommend, agent-tags)
# Then crud router (has list tags, get/create/update/delete tag, references)
router.include_router(list_router)
router.include_router(crud_router)
