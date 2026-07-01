"""Settings API - 路由端点"""

import httpx
import json
from loguru import logger
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models.system_config import SystemConfig

from .settings_models import ConfigValueUpdate, BatchUpdateRequest, TestConnectionResponse
from .settings_logic import _parse_value, _get_config_value, _get_category_configs, _get_gateway_config

router = APIRouter()

@router.get("/")
async def get_all_settings(db: Session = Depends(get_db)):
    """获取所有配置（按 category 分组）"""
    results = db.query(distinct(SystemConfig.category)).order_by(SystemConfig.category).all()
    categories = [row[0] for row in results]
    all_settings = {}
    for cat in categories:
        all_settings[cat] = _get_category_configs(db, cat)
    return all_settings

@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_openclaw_connection(db: Session = Depends(get_db)):
    """测试 OpenClaw 连接"""
    gateway_url, token_config = _get_gateway_config(db)
    start_time = datetime.utcnow()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if token_config and token_config["value"]:
                headers["Authorization"] = f"Bearer {token_config['value']}"
            response = await client.get(f"{gateway_url}/api/v1/health", headers=headers)
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            if response.status_code == 200:
                return TestConnectionResponse(
                    status="connected",
                    message="OpenClaw Gateway 连接正常",
                    gateway_url=gateway_url,
                    response_time_ms=elapsed_ms,
                    details=response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
                )
            else:
                return TestConnectionResponse(
                    status="failed",
                    message=f"连接失败: HTTP {response.status_code}",
                    gateway_url=gateway_url,
                    response_time_ms=elapsed_ms,
                )
    except httpx.ConnectError:
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return TestConnectionResponse(status="failed", message=f"无法连接到 OpenClaw Gateway ({gateway_url})，请检查服务是否启动", gateway_url=gateway_url, response_time_ms=elapsed_ms)
    except httpx.TimeoutException:
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return TestConnectionResponse(status="failed", message="连接超时", gateway_url=gateway_url, response_time_ms=elapsed_ms)
    except Exception as e:
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return TestConnectionResponse(status="failed", message=f"连接测试异常: {str(e)}", gateway_url=gateway_url, response_time_ms=elapsed_ms)

@router.get("/models")
async def get_available_models(db: Session = Depends(get_db)):
    """从 OpenClaw API 获取可用模型列表"""
    gateway_url, token_config = _get_gateway_config(db)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if token_config and token_config["value"]:
                headers["Authorization"] = f"Bearer {token_config['value']}"
            response = await client.get(f"{gateway_url}/api/v1/models", headers=headers)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    models = [{"id": m.get("id", m), "name": m.get("name", m.get("id", m)), "provider": m.get("provider")} for m in data]
                elif isinstance(data, dict) and "data" in data:
                    models = [{"id": m.get("id", m), "name": m.get("name", m.get("id", m)), "provider": m.get("provider")} for m in data["data"]]
                else:
                    models = []
                return {"models": models, "source": "openclaw"}
            else:
                return {"models": [], "source": "openclaw", "error": f"HTTP {response.status_code}"}
    except Exception:
        fallback_models = [
            {"id": "minimax/MiniMax-M2.7-highspeed", "name": "MiniMax M2.7 Highspeed", "provider": "minimax"},
            {"id": "minimax/MiniMax-M2.7", "name": "MiniMax M2.7", "provider": "minimax"},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openai"},
            {"id": "anthropic/claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "anthropic"},
            {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "google"},
        ]
        return {"models": fallback_models, "source": "fallback", "warning": "无法连接 OpenClaw，返回默认模型列表"}

@router.get("/sessions")
async def get_openclaw_sessions(db: Session = Depends(get_db)):
    """获取当前 OpenClaw session 列表"""
    gateway_url, token_config = _get_gateway_config(db)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if token_config and token_config["value"]:
                headers["Authorization"] = f"Bearer {token_config['value']}"
            response = await client.get(f"{gateway_url}/api/v1/sessions", headers=headers)
            if response.status_code == 200:
                data = response.json()
                sessions = data if isinstance(data, list) else data.get("sessions", [])
                return {"sessions": sessions}
            else:
                return {"sessions": [], "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"sessions": [], "error": str(e)}

# ========== Parameterized Routes (MUST be after specific routes) ==========

@router.get("/{category}")
async def get_settings_by_category(category: str, db: Session = Depends(get_db)):
    """获取某类配置"""
    configs = _get_category_configs(db, category)
    if not configs:
        count = db.query(func.count(SystemConfig.id)).filter(SystemConfig.category == category).scalar()
        if count == 0:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
    return configs

@router.put("/{category}/batch")
async def batch_update_settings(category: str, body: BatchUpdateRequest, db: Session = Depends(get_db)):
    """批量更新配置"""
    now = datetime.utcnow()
    updated = []
    errors = []
    for key, value in body.configs.items():
        existing = _get_config_value(db, category, key)
        if not existing:
            errors.append({"key": key, "error": "not found"})
            continue
        if isinstance(value, (dict, list, bool)):
            value_str = json.dumps(value)
        elif isinstance(value, (int, float)):
            value_str = str(value)
        elif value is None:
            value_str = '""'
        else:
            value_str = json.dumps(str(value))
        db.query(SystemConfig).filter(
            SystemConfig.category == category, SystemConfig.key == key
        ).update({"value": value_str, "updated_at": now, "updated_by": "admin"})
        updated.append(key)
    db.commit()
    return {"status": "ok", "updated": updated, "errors": errors, "count": len(updated)}

@router.get("/{category}/{key}")
async def get_single_setting(category: str, key: str, db: Session = Depends(get_db)):
    """获取单个配置项"""
    config = _get_config_value(db, category, key)
    if not config:
        raise HTTPException(status_code=404, detail=f"Config '{category}/{key}' not found")
    return {
        "key": config["key"], "value": config["value"],
        "description": config["description"], "updated_at": config["updated_at"],
        "updated_by": config["updated_by"],
    }

@router.put("/{category}/{key}")
async def update_setting(category: str, key: str, body: ConfigValueUpdate, db: Session = Depends(get_db)):
    """更新单个配置"""
    existing = _get_config_value(db, category, key)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Config '{category}/{key}' not found")
    now = datetime.utcnow()
    db.query(SystemConfig).filter(
        SystemConfig.category == category, SystemConfig.key == key
    ).update({"value": body.value, "updated_at": now, "updated_by": "admin"})
    db.commit()
    logger.info(f"Config updated: {category}/{key} = {body.value}")
    return {
        "status": "ok", "category": category, "key": key,
        "value": _parse_value(body.value), "updated_at": now.isoformat(),
    }
