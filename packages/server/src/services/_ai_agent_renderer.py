# -*- coding: utf-8 -*-
"""Context validation and prompt rendering."""
import json
import re
from typing import Any, Dict, Optional

from loguru import logger


def validate_context(
    context: Dict[str, Any],
    context_schema: Optional[Dict[str, Any]]
) -> bool:
    """Validate context against schema."""
    if not context_schema:
        return True
    if isinstance(context_schema, str):
        try:
            context_schema = json.loads(context_schema)
        except json.JSONDecodeError:
            logger.warning("[validate_context] Invalid context_schema JSON")
            return True
    for field_name, field_spec in context_schema.items():
        if isinstance(field_spec, dict):
            required = field_spec.get("required", False)
            if required and field_name not in context:
                raise ValueError(
                    f"Required context field missing: '{field_name}'. "
                    f"Required fields for this template: "
                    f"{[k for k, v in context_schema.items() if isinstance(v, dict) and v.get('required')]}"
                )
    return True


def render_prompt(template: str, context: Dict[str, Any]) -> str:
    """Render prompt template with context variables.

    Supports {variable} and {variable|default} syntax.
    """
    if not template:
        return ""
    result = template
    for key, value in context.items():
        placeholder = "{" + key + "}"
        if placeholder in result:
            result = result.replace(placeholder, _format_value(value))

    def replace_optional(match):
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) else ""
        value = context.get(var_name)
        if value is None or value == "":
            return default_val
        return _format_value(value)

    result = re.sub(r'\{(\w+)\|([^}]*)\}', replace_optional, result)
    result = re.sub(r'\{\w+\}', '', result)
    return result


def _format_value(value: Any) -> str:
    """Format a value for prompt insertion."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)
