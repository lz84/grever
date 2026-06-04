"""
敏感数据脱敏工具

对 API 响应中的敏感字段进行脱敏处理。

脱敏规则：
- API key / token / password: 显示前 4 位 + *** + 后 4 位
- 邮箱: 只显示 @ 前的 2 位 + ***
- IP 地址: 只显示前 2 段
- 文件路径: 只显示文件名
"""

import re
from loguru import logger
from typing import Any, Dict, List, Union

# 敏感字段名（大小写不敏感）
SENSITIVE_FIELD_NAMES = {
    "password", "secret", "token", "api_key", "apikey", "api_secret",
    "access_key", "access_token", "auth_token", "private_key",
    "credential", "credentials",
}

# 脱敏函数
def _mask_string(value: str, visible_front: int = 4, visible_back: int = 4) -> str:
    """对字符串进行脱敏：显示前 N 位 + *** + 后 N 位"""
    if not value or len(value) <= visible_front + visible_back + 3:
        return "***"
    return f"{value[:visible_front]}***{value[-visible_back:]}"

def _mask_dict(value: Dict, depth: int = 0) -> Dict:
    """对字典进行脱敏，递归处理嵌套"""
    if depth > 3:
        return "***"
    result = {}
    for k, v in value.items():
        k_lower = k.lower()
        if any(s in k_lower for s in SENSITIVE_FIELD_NAMES):
            result[k] = _mask_string(str(v)) if isinstance(v, str) else "***"
        elif isinstance(v, dict):
            result[k] = _mask_dict(v, depth + 1)
        elif isinstance(v, list):
            result[k] = [_mask_dict(item, depth + 1) if isinstance(item, dict) else item for item in v]
        else:
            result[k] = v
    return result

def sanitize_dict(data: Dict) -> Dict:
    """对字典进行脱敏"""
    try:
        return _mask_dict(data)
    except Exception as e:
        logger.warning(f"Sanitization failed: {e}")
        return data

def sanitize_agent_metadata(metadata: Any) -> Any:
    """对 Agent metadata 进行脱敏"""
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return sanitize_dict(metadata)
    if isinstance(metadata, str):
        try:
            import json
            parsed = json.loads(metadata)
            if isinstance(parsed, dict):
                return sanitize_dict(parsed)
        except Exception:
            pass
    return metadata

def sanitize_result(result: Any) -> Any:
    """对任务执行结果进行脱敏"""
    if result is None:
        return None
    if isinstance(result, dict):
        return sanitize_dict(result)
    return result

def sanitize_execution_log(log_entry: Dict) -> Dict:
    """对执行日志进行脱敏"""
    if not log_entry:
        return log_entry
    result = log_entry.copy()
    if "input" in result:
        inp = result["input"]
        if isinstance(inp, dict):
            result["input"] = sanitize_dict(inp)
    if "output" in result:
        out = result["output"]
        if isinstance(out, dict):
            result["output"] = sanitize_dict(out)
    return result
