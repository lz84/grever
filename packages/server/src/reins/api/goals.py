"""Goals API facade: merges CRUD, list, and tree routers.
goals_exploration is imported separately in server.py to avoid duplicates."""
from fastapi import APIRouter
from reins.api.goals_crud import router as goals_crud_router
from reins.api.goals_list import router as goals_list_router
from reins.api.goal_tree import router as goal_tree_router

router = APIRouter()
for r in [goals_crud_router, goals_list_router, goal_tree_router]:
    router.include_router(r)
