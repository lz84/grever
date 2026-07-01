"""Settings API - 辅助逻辑函数"""

import json
from typing import Optional

from sqlalchemy.orm import Session

from models.system_config import SystemConfig


def _parse_value(raw_value: str) -> str:
    """解析配置值，去除 JSON 字符串引号"""
    try:
        parsed = json.loads(raw_value)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return raw_value

def _get_config_value(db: Session, category: str, key: str) -> Optional[dict]:
    """获取单个配置值"""
    result = db.query(SystemConfig).filter(
        SystemConfig.category == category,
        SystemConfig.key == key
    ).first()
    if not result:
        return None
    return {
        "id": result.id, "category": result.category, "key": result.key,
        "value": _parse_value(result.value), "description": result.description,
        "updated_at": result.updated_at, "updated_by": result.updated_by,
    }

def _get_category_configs(db: Session, category: str) -> dict:
    """获取某个 category 的所有配置"""
    results = db.query(SystemConfig).filter(
        SystemConfig.category == category
    ).order_by(SystemConfig.key).all()
    configs = {}
    for row in results:
        raw_val = row.value
        try:
            parsed = json.loads(raw_val)
            val_type = type(parsed).__name__
            parsed_val = parsed
        except (json.JSONDecodeError, TypeError):
            val_type = "string"
            parsed_val = raw_val
        configs[row.key] = {
            "value": parsed_val, "type": val_type,
            "description": row.description, "updated_at": row.updated_at, "updated_by": row.updated_by,
        }
    return configs

def _get_gateway_config(db: Session) -> tuple:
    """获取 OpenClaw Gateway URL 和 token，返回 (gateway_url, token_config)"""
    gateway_config = _get_config_value(db, "openclaw", "gateway_url")
    token_config = _get_config_value(db, "openclaw", "api_token")
    gateway_url = "http://127.0.0.1:8080"
    if gateway_config:
        gateway_url = gateway_config["value"]
    if not gateway_url.startswith("http"):
        gateway_url = f"http://{gateway_url}"
    return gateway_url, token_config
