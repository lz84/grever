# -*- coding: utf-8 -*-
"""JSON response parsing from agent output."""
import json
import re
from typing import Any, Dict, Optional

from loguru import logger


def parse_json_response(
    result: Dict[str, Any],
    output_schema: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Parse raw text response into structured JSON.

    Tries multiple strategies:
    1. Look for JSON code blocks in raw_response
    2. Try to parse entire raw_response as JSON
    3. Look for {...} or [...] patterns
    4. Return raw text in 'text' field
    """
    raw_response = result.get("raw_response", "")
    if not raw_response or raw_response in ("Agent response timeout", ""):
        return result

    # Strategy 1: Look for ```json ... ``` code blocks
    code_blocks = re.findall(r"```json\s*(.*?)\s*```", raw_response, re.DOTALL)
    if code_blocks:
        for block in code_blocks:
            try:
                parsed = json.loads(block.strip())
                if isinstance(parsed, dict):
                    logger.info("[parse_json_response] Parsed JSON from code block")
                    return {**result, **parsed, "_raw_parsed": True}
            except (json.JSONDecodeError, TypeError):
                continue

    # Strategy 2: Look for ``` ... ``` blocks (non-json)
    code_blocks = re.findall(r"```\s*(.*?)\s*```", raw_response, re.DOTALL)
    for block in code_blocks:
        block = block.strip()
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict):
                logger.info("[parse_json_response] Parsed JSON from code block (no lang)")
                return {**result, **parsed, "_raw_parsed": True}
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 3: Try parsing entire raw_response as JSON
    try:
        parsed = json.loads(raw_response.strip())
        if isinstance(parsed, dict):
            logger.info("[parse_json_response] Parsed entire response as JSON")
            return {**result, **parsed, "_raw_parsed": True}
        elif isinstance(parsed, list):
            logger.info("[parse_json_response] Parsed response as JSON array")
            return {**result, "items": parsed, "_raw_parsed": True}
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 4: Look for {...} or [...] patterns
    json_patterns = [r'\{[^{}]*\}', r'\[[^\[\]]*\]']
    for pattern in json_patterns:
        matches = re.findall(pattern, raw_response, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict) and len(parsed) >= 2:
                    logger.info("[parse_json_response] Parsed JSON from pattern match")
                    return {**result, **parsed, "_raw_parsed": True}
            except (json.JSONDecodeError, TypeError):
                continue

    # Strategy 5: No JSON found, return raw text
    logger.info("[parse_json_response] No JSON found, returning raw text")
    return {**result, "text": raw_response[:2000], "_raw_parsed": False}
