"""
Agents Router — facade
Agent CRUD / 心跳 / 发现 / 心跳日志
子模块: _agents_register_routes, _agents_heartbeat_routes,
        _agents_discover_routes, _agents_manage_routes
"""
import json
import time
from loguru import logger
import uuid as _uuid_lib
import datetime
from datetime import datetime as _dt
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy import text
from pydantic import BaseModel, Field

from api.app_state import get_reins, get_db_manager

# ── Submodule routers (no prefix — facade provides /api/v1) ──
from reins.api._agents_register_routes import router as _register_router
from reins.api._agents_heartbeat_routes import router as _heartbeat_router
from reins.api._agents_discover_routes import router as _discover_router
from reins.api._agents_manage_routes import router as _manage_router

router = APIRouter(prefix="/api/v1", tags=["agents"])
router.include_router(_register_router)
router.include_router(_heartbeat_router)
router.include_router(_discover_router)
router.include_router(_manage_router)

# ── Re-export models for backwards compat ──
# (inlined from _agents_models stub)
from reins.api._agents_register_routes import AgentRegister, AgentResponse, HeartbeatRequest
