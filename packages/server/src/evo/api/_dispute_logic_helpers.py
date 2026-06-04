"""Shared helpers and DisputeLogic base class for dispute submodules."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid

from reins.common.database import get_db_manager
from sqlalchemy import text

class DisputeLogic:
    """争议管理业务逻辑"""

    def __init__(self):
        self._engine = get_db_manager().engine

    def _row_to_dict(self, row) -> dict:
        return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)

    def _parse_json_field(self, val):
        if val is None:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        return val

    def _get_dispute_row(self, dispute_id: str) -> Optional[dict]:
        with self._engine.connect() as conn:
            row = conn.execute(text(
                "SELECT * FROM disputes WHERE id = :id"
            ), {"id": dispute_id}).fetchone()
            return self._row_to_dict(row) if row else None

    def _append_discussion_log(self, dispute_id: str, entry: dict):
        with self._engine.begin() as conn:
            row = conn.execute(text("SELECT discussion_log FROM disputes WHERE id = :id"), {"id": dispute_id}).fetchone()
            log = []
            if row and row[0]:
                try:
                    log = json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    pass
            log.append(entry)
            conn.execute(text("UPDATE disputes SET discussion_log = :log, updated_at = :now WHERE id = :id"), {
                "id": dispute_id, "log": json.dumps(log, ensure_ascii=False), "now": datetime.now().isoformat(),
            })

    def _get_timeline(self, dispute_id: str) -> List[dict]:
        with self._engine.connect() as conn:
            row = conn.execute(text(
                "SELECT discussion_log FROM disputes WHERE id = :id"
            ), {"id": dispute_id}).fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    pass
        return []

    def raise_dispute(self, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        dispute_id = f"disp-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        with self._engine.connect() as conn:
            goal_id = None
            if req.get("related_task_id"):
                row = conn.execute(text(
                    "SELECT goal_id FROM tasks WHERE id = :task_id"
                ), {"task_id": req["related_task_id"]}).fetchone()
                if row:
                    goal_id = row[0]
                else:
                    raise HTTPException(404, f"相关任务不存在: {req['related_task_id']}")
            elif req.get("goal_id"):
                goal_id = req["goal_id"]
            conn.commit()
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO disputes
                (id, dispute_type, description, involved_agents, related_task_id, goal_id,
                 raised_by_agent, status, created_at, updated_at)
                VALUES (:id, :dtype, :desc, :agents, :task_id, :goal_id, :raised_by, 'open', :now, :now)
            """), {
                "id": dispute_id,
                "dtype": req.get("dispute_type"),
                "desc": req.get("description"),
                "agents": json.dumps(req.get("involved_agents", []), ensure_ascii=False),
                "task_id": req.get("related_task_id"),
                "goal_id": goal_id,
                "raised_by": req.get("raised_by_agent"),
                "now": now,
            })
        from evo.api.dispute_manage import DisputeResponse
        return DisputeResponse(
            id=dispute_id, dispute_type=req.get("dispute_type"),
            description=req.get("description"),
            involved_agents=req.get("involved_agents", []),
            related_task_id=req.get("related_task_id"), goal_id=goal_id,
            status="open", resolution=None, resolved_by=None,
            created_at=now, updated_at=now, resolved_at=None,
        )

    def list_disputes(self, status: Optional[str] = None, goal_id: Optional[str] = None):
        with self._engine.connect() as conn:
            conditions, params = [], {}
            if goal_id:
                conditions.append("goal_id = :goal_id")
                params["goal_id"] = goal_id
            if status:
                conditions.append("status = :status")
                params["status"] = status
            where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            rows = conn.execute(text(
                f"SELECT * FROM disputes {where_clause} ORDER BY created_at DESC"
            ), params).fetchall()
        result = []
        for row in rows:
            d = self._row_to_dict(row)
            from evo.api.dispute_manage import DisputeResponse
            result.append(DisputeResponse(
                id=d["id"], dispute_type=d["dispute_type"], description=d["description"],
                involved_agents=self._parse_json_field(d.get("involved_agents")),
                related_task_id=d.get("related_task_id"), goal_id=d.get("goal_id"),
                status=d["status"], resolution=d.get("resolution"),
                resolved_by=d.get("resolved_by"), created_at=d["created_at"],
                updated_at=d["updated_at"], resolved_at=d.get("resolved_at"),
            ))
        return result

    def get_dispute_stats(self):
        from evo.api.dispute_manage import DisputeStatsResponse
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, dispute_type, status FROM disputes"
            )).fetchall()
        stats = {
            "total": len(rows),
            "open": 0, "discussing": 0, "resolved": 0, "escalated": 0, "closed": 0,
            "by_type": {},
        }
        for row in rows:
            st = row[2]
            if st in stats:
                stats[st] += 1
            dt = row[1]
            stats["by_type"][dt] = stats["by_type"].get(dt, 0) + 1
        return DisputeStatsResponse(**stats)

    def get_dispute(self, dispute_id: str):
        from fastapi import HTTPException
        from evo.api.dispute_manage import DisputeResponse
        d = self._get_dispute_row(dispute_id)
        if not d:
            raise HTTPException(404, "Dispute not found")
        return DisputeResponse(
            id=d["id"], dispute_type=d["dispute_type"], description=d["description"],
            involved_agents=self._parse_json_field(d.get("involved_agents")),
            related_task_id=d.get("related_task_id"), goal_id=d.get("goal_id"),
            status=d["status"], resolution=d.get("resolution"),
            resolved_by=d.get("resolved_by"), created_at=d["created_at"],
            updated_at=d["updated_at"], resolved_at=d.get("resolved_at"),
        )

    def resolve_dispute(self, dispute_id: str, resolution: str, resolved_by: Optional[str] = None):
        from fastapi import HTTPException
        from evo.api.dispute_manage import DisputeResponse
        d = self._get_dispute_row(dispute_id)
        if not d:
            raise HTTPException(404, "Dispute not found")
        now = datetime.now().isoformat()
        with self._engine.begin() as conn:
            conn.execute(text("""
                UPDATE disputes SET status = 'resolved', resolution = :res, resolved_by = :by,
                    resolved_at = :now, updated_at = :now WHERE id = :id
            """), {"id": dispute_id, "res": resolution, "by": resolved_by, "now": now})
        d["status"] = "resolved"
        d["resolution"] = resolution
        d["resolved_by"] = resolved_by
        d["resolved_at"] = now
        d["updated_at"] = now
        return DisputeResponse(
            id=d["id"], dispute_type=d["dispute_type"], description=d["description"],
            involved_agents=self._parse_json_field(d.get("involved_agents")),
            related_task_id=d.get("related_task_id"), status=d["status"],
            resolution=d.get("resolution"), resolved_by=d.get("resolved_by"),
            created_at=d["created_at"], updated_at=d["updated_at"],
            resolved_at=d.get("resolved_at"),
        )

    def add_discussion(self, dispute_id: str, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        wf = self._get_dispute_row(dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        if wf["status"] not in ("open", "discussing"):
            raise HTTPException(400, f"争议状态为 '{wf['status']}'，仅 open/discussing 状态可讨论")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": req.get("agent_id"), "action": "discussed",
            "message": req.get("message"),
        }
        self._append_discussion_log(dispute_id, entry)
        if wf["status"] == "open":
            with self._engine.begin() as conn:
                conn.execute(text(
                    "UPDATE disputes SET status = :status, updated_at = :now WHERE id = :id"
                ), {"id": dispute_id, "status": "discussing", "now": datetime.now().isoformat()})
        return {"success": True, "message": "讨论消息已添加"}

    def update_dispute_status(self, dispute_id: str, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        wf = self._get_dispute_row(dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        new_status = req.get("new_status")
        valid_statuses = ("open", "discussing", "resolved", "escalated", "closed")
        if new_status not in valid_statuses:
            raise HTTPException(400, f"无效状态: {new_status}")
        now = datetime.now().isoformat()
        with self._engine.begin() as conn:
            conn.execute(text(
                "UPDATE disputes SET status = :status, updated_at = :now WHERE id = :id"
            ), {"id": dispute_id, "status": new_status, "now": now})
        entry = {
            "timestamp": now, "agent_id": "system", "action": "status_changed",
            "message": f"状态从 '{wf['status']}' 变为 '{new_status}'",
            "metadata": {"old_status": wf["status"], "new_status": new_status},
        }
        self._append_discussion_log(dispute_id, entry)
        return {"success": True, "dispute_id": dispute_id, "new_status": new_status}

    def arbitrate_dispute(self, dispute_id: str, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        wf = self._get_dispute_row(dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        now = datetime.now().isoformat()
        with self._engine.begin() as conn:
            conn.execute(text("""
                UPDATE disputes SET status = 'resolved', resolution = :resolution,
                    resolved_by = :arbitrator, resolved_at = :now, updated_at = :now
                WHERE id = :id
            """), {"id": dispute_id, "resolution": req.get("resolution"),
                    "arbitrator": req.get("arbitrator", "human"), "now": now})
        entry = {
            "timestamp": now, "agent_id": req.get("arbitrator", "human"),
            "action": "arbitrated", "message": req.get("resolution"),
        }
        self._append_discussion_log(dispute_id, entry)
        return {"success": True, "dispute_id": dispute_id, "resolution": req.get("resolution")}

    def get_dispute_timeline(self, dispute_id: str):
        from fastapi import HTTPException
        from evo.api.dispute_manage import TimelineResponse, TimelineEntry
        wf = self._get_dispute_row(dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        entries = self._get_timeline(dispute_id)
        if not entries or entries[0].get("action") != "raised":
            raised_entry = {
                "timestamp": wf["created_at"],
                "agent_id": wf.get("raised_by_agent") or "unknown",
                "action": "raised", "message": wf["description"],
                "metadata": {"dispute_type": wf["dispute_type"]},
            }
            entries.insert(0, raised_entry)
        return TimelineResponse(
            dispute_id=dispute_id, entries=[TimelineEntry(**e) for e in entries],
        )

    def get_dispute_detail(self, dispute_id: str):
        from fastapi import HTTPException
        from evo.api.dispute_manage import DisputeDetailResponse
        wf = self._get_dispute_row(dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        entries = self._get_timeline(dispute_id)
        return DisputeDetailResponse(
            id=wf["id"], dispute_type=wf["dispute_type"], description=wf["description"],
            involved_agents=self._parse_json_field(wf.get("involved_agents")),
            related_task_id=wf.get("related_task_id"), status=wf["status"],
            raised_by_agent=wf.get("raised_by_agent"), resolution=wf.get("resolution"),
            resolved_by=wf.get("resolved_by"), created_at=wf["created_at"],
            updated_at=wf["updated_at"], resolved_at=wf.get("resolved_at"),
            deadline=wf.get("deadline"), discussion_count=len(entries),
        )
