"""Industry Capability Tags — Helpers and shared utilities."""
import json
from typing import Optional, List

from sqlalchemy import text

from reach.industry.api.industry_tag_models import (
    IndustryCapabilityTagResponse,
    TagListResponse,
    compute_version_change,
)


def _row_to_response(row) -> IndustryCapabilityTagResponse:
    """Convert a DB row to IndustryCapabilityTagResponse."""
    return IndustryCapabilityTagResponse(
        id=row[0], industry=row[1], tag_name=row[2], tag_name_en=row[3],
        description=row[4], dimension=row[5], level=row[6],
        prerequisites=_parse_json(row[7]), tools=_parse_json(row[8]),
        examples=_parse_json(row[9]), status=row[10],
        created_at=row[11], updated_at=row[12],
        replaced_by=row[13] if len(row) > 13 else None,
        version_major=row[14] if len(row) > 14 else 1,
        version_minor=row[15] if len(row) > 15 else 0,
        version_patch=row[16] if len(row) > 16 else 0,
    )


def _parse_json(value) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _to_json(value) -> str:
    if value is None:
        return '[]'
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _parse_json_safe(v):
    if not v:
        return []
    try:
        return json.loads(v)
    except Exception:
        return []


def _count_tag_references(tag_id: str, db) -> dict:
    """Count how many Tasks, Scenarios, and Agents reference a given tag_id."""
    task_count, scenario_count, agent_count = 0, 0, 0

    task_rows = db.execute(text("SELECT id, title, capability_tags FROM tasks")).fetchall()
    for row in task_rows:
        if not row[2]: continue
        try:
            caps = json.loads(row[2]) if isinstance(row[2], str) else row[2]
        except Exception: continue
        if not isinstance(caps, dict): continue
        for dim_tags in caps.values():
            if isinstance(dim_tags, list) and tag_id in dim_tags:
                task_count += 1
                break

    scenario_rows = db.execute(text("SELECT id, name, goal_capability_tags FROM scenarios")).fetchall()
    for row in scenario_rows:
        if not row[2]: continue
        try:
            reqs = json.loads(row[2]) if isinstance(row[2], str) else row[2]
        except Exception: continue
        if isinstance(reqs, list) and tag_id in reqs:
            scenario_count += 1

    agent_rows = db.execute(text("SELECT id, name, capability_tags FROM agents")).fetchall()
    for row in agent_rows:
        if not row[2]: continue
        try:
            caps = json.loads(row[2]) if isinstance(row[2], str) else row[2]
        except Exception: continue
        if not isinstance(caps, dict): continue
        for dim_tags in caps.values():
            if isinstance(dim_tags, list) and tag_id in dim_tags:
                agent_count += 1
                break

    return {"task_count": task_count, "scenario_count": scenario_count,
            "agent_count": agent_count, "total_count": task_count + scenario_count + agent_count}
