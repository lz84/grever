"""
成果物辅助函数
从 artifacts.py 拆分
"""
import json

def _parse_json_field(val):
    if val is None:
        return []
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []
    return val

def _row_to_artifact(row) -> dict:
    tags = _parse_json_field(row.get("tags"))
    return {
        "id": row["id"],
        "task_id": row.get("task_id"),
        "project_id": row.get("project_id"),
        "goal_id": row.get("goal_id"),
        "created_by": row["created_by"],
        "name": row["name"],
        "type": row.get("type", "other"),
        "url": row.get("url"),
        "size": row.get("size", 0),
        "description": row.get("description"),
        "tags": tags,
        "created_at": row["created_at"],
    }
