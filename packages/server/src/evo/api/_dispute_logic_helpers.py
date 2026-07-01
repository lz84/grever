"""Shared helpers and DisputeLogic base class for dispute submodules.

所有方法接收 session 参数，由调用方（API 路由）通过 Depends(get_db) 管理生命周期。
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session
from models.dispute import Dispute
from models.task import Task

class DisputeLogic:
    """争议管理业务逻辑
    
    ⚠️ 所有方法都要求调用方传入 session，不自建 session。
    调用方必须通过 FastAPI Depends(get_db) 获取 session。
    """

    def _row_to_dict(self, row) -> dict:
        if hasattr(row, 'to_dict'):
            return row.to_dict()
        if hasattr(row, '_mapping'):
            return dict(row._mapping)
        d = {}
        for col in row.__table__.columns:
            val = getattr(row, col.name, None)
            if isinstance(val, datetime):
                d[col.name] = val.isoformat()
            else:
                d[col.name] = val
        return d

    def _parse_json_field(self, val):
        if val is None:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []
        return val

    def _get_dispute_row(self, session: Session, dispute_id: str) -> Optional[dict]:
        row = session.query(Dispute).filter(Dispute.id == dispute_id).first()
        return self._row_to_dict(row.__dict__) if row else None

    def _append_discussion_log(self, session: Session, dispute_id: str, entry: dict):
        row = session.query(Dispute).filter(Dispute.id == dispute_id).first()
        log = []
        if row and row.discussion_log:
            try:
                log = json.loads(row.discussion_log)
            except (json.JSONDecodeError, TypeError):
                pass
        log.append(entry)
        session.query(Dispute).filter(Dispute.id == dispute_id).update({
            "discussion_log": json.dumps(log, ensure_ascii=False),
            "updated_at": datetime.now().isoformat(),
        })
        session.commit()

    def _get_timeline(self, session: Session, dispute_id: str) -> List[dict]:
        row = session.query(Dispute).filter(Dispute.id == dispute_id).first()
        if row and row.discussion_log:
            try:
                return json.loads(row.discussion_log)
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    def raise_dispute(self, session: Session, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        dispute_id = f"disp-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        goal_id = None
        if req.get("related_task_id"):
            task = session.query(Task).filter(Task.id == req["related_task_id"]).first()
            if task:
                goal_id = task.goal_id
            else:
                raise HTTPException(404, f"相关任务不存在: {req['related_task_id']}")
        elif req.get("goal_id"):
            goal_id = req["goal_id"]
        
        new_dispute = Dispute(
            id=dispute_id,
            dispute_type=req.get("dispute_type"),
            description=req.get("description"),
            involved_agents=json.dumps(req.get("involved_agents", []), ensure_ascii=False),
            related_task_id=req.get("related_task_id"),
            goal_id=goal_id,
            raised_by_agent=req.get("raised_by_agent"),
            status="open",
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )
        session.add(new_dispute)
        session.commit()
        
        from evo.api.dispute_manage import DisputeResponse
        return DisputeResponse(
            id=dispute_id, dispute_type=req.get("dispute_type"),
            description=req.get("description"),
            involved_agents=req.get("involved_agents", []),
            related_task_id=req.get("related_task_id"), goal_id=goal_id,
            status="open", resolution=None, resolved_by=None,
            created_at=now, updated_at=now, resolved_at=None,
        )

    def list_disputes(self, session: Session, status: Optional[str] = None, goal_id: Optional[str] = None):
        query = session.query(Dispute)
        if goal_id:
            query = query.filter(Dispute.goal_id == goal_id)
        if status:
            query = query.filter(Dispute.status == status)
        rows = query.order_by(Dispute.created_at.desc()).all()
        result = []
        for row in rows:
            d = row.to_dict()
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

    def get_dispute_stats(self, session: Session):
        from evo.api.dispute_manage import DisputeStatsResponse
        rows = session.query(Dispute.id, Dispute.dispute_type, Dispute.status).all()
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

    def get_dispute(self, session: Session, dispute_id: str):
        from fastapi import HTTPException
        from evo.api.dispute_manage import DisputeResponse
        d = self._get_dispute_row(session, dispute_id)
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

    def resolve_dispute(self, session: Session, dispute_id: str, resolution: str, resolved_by: Optional[str] = None):
        from fastapi import HTTPException
        from evo.api.dispute_manage import DisputeResponse
        d = self._get_dispute_row(session, dispute_id)
        if not d:
            raise HTTPException(404, "Dispute not found")
        now = datetime.now().isoformat()
        session.query(Dispute).filter(Dispute.id == dispute_id).update({
            "status": "resolved",
            "resolution": resolution,
            "resolved_by": resolved_by,
            "resolved_at": datetime.fromisoformat(now),
            "updated_at": datetime.fromisoformat(now),
        })
        session.commit()
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

    def add_discussion(self, session: Session, dispute_id: str, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        wf = self._get_dispute_row(session, dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        if wf["status"] not in ("open", "discussing"):
            raise HTTPException(400, f"争议状态为 '{wf['status']}'，仅 open/discussing 状态可讨论")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": req.get("agent_id"), "action": "discussed",
            "message": req.get("message"),
        }
        self._append_discussion_log(session, dispute_id, entry)
        if wf["status"] == "open":
            session.query(Dispute).filter(Dispute.id == dispute_id).update({
                "status": "discussing",
                "updated_at": datetime.fromisoformat(datetime.now().isoformat()),
            })
            session.commit()
        return {"success": True, "message": "讨论消息已添加"}

    def update_dispute_status(self, session: Session, dispute_id: str, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        wf = self._get_dispute_row(session, dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        new_status = req.get("new_status")
        valid_statuses = ("open", "discussing", "resolved", "escalated", "closed")
        if new_status not in valid_statuses:
            raise HTTPException(400, f"无效状态: {new_status}")
        now = datetime.now().isoformat()
        session.query(Dispute).filter(Dispute.id == dispute_id).update({
            "status": new_status,
            "updated_at": datetime.fromisoformat(now),
        })
        session.commit()
        entry = {
            "timestamp": now, "agent_id": "system", "action": "status_changed",
            "message": f"状态从 '{wf['status']}' 变为 '{new_status}'",
            "metadata": {"old_status": wf["status"], "new_status": new_status},
        }
        self._append_discussion_log(session, dispute_id, entry)
        return {"success": True, "dispute_id": dispute_id, "new_status": new_status}

    def arbitrate_dispute(self, session: Session, dispute_id: str, req):
        from fastapi import HTTPException
        if hasattr(req, 'model_dump'):
            req = req.model_dump()
        wf = self._get_dispute_row(session, dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        now = datetime.now().isoformat()
        session.query(Dispute).filter(Dispute.id == dispute_id).update({
            "status": "resolved",
            "resolution": req.get("resolution"),
            "resolved_by": req.get("arbitrator", "human"),
            "resolved_at": datetime.fromisoformat(now),
            "updated_at": datetime.fromisoformat(now),
        })
        session.commit()
        entry = {
            "timestamp": now, "agent_id": req.get("arbitrator", "human"),
            "action": "arbitrated", "message": req.get("resolution"),
        }
        self._append_discussion_log(session, dispute_id, entry)
        return {"success": True, "dispute_id": dispute_id, "resolution": req.get("resolution")}

    def get_dispute_timeline(self, session: Session, dispute_id: str):
        from fastapi import HTTPException
        from evo.api.dispute_manage import TimelineResponse, TimelineEntry
        wf = self._get_dispute_row(session, dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        entries = self._get_timeline(session, dispute_id)
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

    def get_dispute_detail(self, session: Session, dispute_id: str):
        from fastapi import HTTPException
        from evo.api.dispute_manage import DisputeDetailResponse
        wf = self._get_dispute_row(session, dispute_id)
        if not wf:
            raise HTTPException(404, "Dispute not found")
        entries = self._get_timeline(session, dispute_id)
        return DisputeDetailResponse(
            id=wf["id"], dispute_type=wf["dispute_type"], description=wf["description"],
            involved_agents=self._parse_json_field(wf.get("involved_agents")),
            related_task_id=wf.get("related_task_id"), status=wf["status"],
            raised_by_agent=wf.get("raised_by_agent"), resolution=wf.get("resolution"),
            resolved_by=wf.get("resolved_by"), created_at=wf["created_at"],
            updated_at=wf["updated_at"], resolved_at=wf.get("resolved_at"),
            deadline=wf.get("deadline"), discussion_count=len(entries),
        )
