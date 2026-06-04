"""
FastAPI 应用扩展 - 注册认证路由
"""

from fastapi import FastAPI
from shared.auth.router import router as auth_router


def register_auth_routes(app: FastAPI) -> None:
    """
    注册认证路由
    
    Args:
        app: FastAPI 应用
    """
    app.include_router(auth_router)
