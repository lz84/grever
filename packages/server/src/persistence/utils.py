"""
Nexus Reins 持久化工具函数
"""

from datetime import datetime
from typing import Any, Optional
import json
import uuid

def generate_id(prefix: str = "id") -> str:
    """生成带前缀的唯一 ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

def serialize_value(value: Any) -> Any:
    """
    序列化值用于数据库存储
    - dict/list -> JSON 字符串
    - datetime -> ISO 格式字符串
    - 其他 -> 原值
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, enum.Enum):
        return value.value
    return value

def deserialize_value(value: str, expected_type: type = None) -> Any:
    """
    反序列化值从数据库读取
    - JSON 字符串 -> dict/list
    - ISO 格式字符串 -> datetime
    - 其他 -> 原值
    """
    if value is None:
        return None
    
    try:
        # 尝试解析 JSON
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass
    
    # 尝试解析 datetime
    if expected_type == datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    
    return value

def get_timestamp() -> datetime:
    """获取当前时间戳"""
    return datetime.now()
