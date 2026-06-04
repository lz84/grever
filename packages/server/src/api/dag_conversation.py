# -*- coding: utf-8 -*-
"""DAG Conversation API — Facade (2026-05-14 重构)"""
from fastapi import APIRouter
from api.dag_conversation_router import router as dag_conversation_router

router = APIRouter()
for _r in [dag_conversation_router]:
    for route in _r.routes:
        router.routes.append(route)
