"""
Agent platforms router — unified registration platform listing & schema

GET /api/v1/agent-platforms
    → 返回所有已注册平台列表

GET /api/v1/agent-platforms/{platform_type}/registration-schema
    → 返回指定平台的注册字段 schema
"""

from __future__ import annotations

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Ensure agent_service package is on sys.path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent_service import get_registry

router = APIRouter(prefix="/api/v1/agent-platforms", tags=["agent-platforms"])


class PlatformInfo(BaseModel):
    type: str
    label: str
    available: bool
    is_session_based: bool


@router.get("", response_model=List[PlatformInfo])
def list_platforms():
    """
    列出所有已注册的平台

    Returns:
        平台列表，含 type / label / available / is_session_based
    """
    registry = get_registry()
    return registry.list_platforms()


@router.get("/{platform_type}/registration-schema")
def get_registration_schema(platform_type: str):
    """
    获取指定平台的注册字段 schema

    Returns:
        {
          "platform_type": "openclaw",
          "platform_label": "OpenClaw",
          "is_session_based": false,
          "fields": [...]
        }
    """
    registry = get_registry()
    if not registry.has(platform_type):
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform_type}")

    schema = registry.get(platform_type).get_registration_fields()
    adapter = registry.get(platform_type)

    return {
        "platform_type": adapter.platform_type,
        "platform_label": adapter.platform_label,
        "is_session_based": adapter.is_session_based(),
        "fields": [
            {
                "key": f.key,
                "label": f.label,
                "type": f.type,
                "required": f.required,
                "placeholder": f.placeholder,
                "description": f.description,
                "default": f.default,
                "options": f.options,
                "validation": f.validation,
                "sensitive": f.sensitive,
            }
            for f in schema
        ],
    }