"""全局 app 状态 — 供 router 共享访问 reins 和 db_manager"""
from loguru import logger
from typing import Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reins.common import ReinsServer
from persistence.database import DatabaseManager

_reins: Optional[ReinsServer] = None
_db_manager: Optional[DatabaseManager] = None
_probe_detector: Optional[Any] = None

def set_reins(r: ReinsServer):
    global _reins
    _reins = r

def set_db_manager(db: DatabaseManager):
    global _db_manager
    _db_manager = db
    logger.info(f"DatabaseManager initialized: {db.engine.url}")

def set_probe_detector(detector):
    global _probe_detector
    _probe_detector = detector

def get_probe_detector():
    return _probe_detector

def get_reins() -> ReinsServer:
    if _reins is None:
        raise RuntimeError("ReinsServer not initialized. Call set_reins() first.")
    return _reins

def get_db_manager() -> DatabaseManager:
    if _db_manager is None:
        raise RuntimeError("DatabaseManager not initialized. Call set_db_manager() first.")
    return _db_manager

def setup_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
