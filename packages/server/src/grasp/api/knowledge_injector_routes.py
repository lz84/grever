"""知识注入 API - 路由端点"""

import sys
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from .knowledge_injector_models import (
    TaskResultInput,
    WorkflowResultInput,
    DisputeResultInput,
    InjectResponse,
)
from .knowledge_injector_storage import _load_history, _save_history, _inject_cognition
from .knowledge_injector_cognition import (
    _generate_cognition_from_task,
    _generate_cognition_from_workflow,
    _generate_cognition_from_dispute,
)

router = APIRouter()

@router.post("/task-result", response_model=InjectResponse)
def inject_task_result(result: TaskResultInput):
    """注入单个任务执行结果到 Grasp 知识库"""
    try:
        cognition = _generate_cognition_from_task(result)
        cognition_id = _inject_cognition(cognition)
        _save_history({
            "id": str(uuid.uuid4()),
            "source_type": "task",
            "source_id": result.task_id,
            "cognition_id": cognition_id,
            "cognition_type": cognition["type"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        })
        return InjectResponse(
            status="success",
            cognition_id=cognition_id,
            cognition_type=cognition["type"],
            message=f"任务结果已注入知识库：{cognition['type']}",
        )
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"注入失败: {str(e)}")

@router.post("/workflow-result", response_model=Dict[str, Any])
def inject_workflow_result(result: WorkflowResultInput):
    """注入工作流执行结果到 Grasp 知识库"""
    try:
        results = {
            "status": "success",
            "workflow_cognition": None,
            "task_cognitions": [],
            "total_injected": 0,
        }
        # 注入工作流整体认知
        wf_cognition = _generate_cognition_from_workflow(result)
        wf_cognition_id = _inject_cognition(wf_cognition)
        results["workflow_cognition"] = {
            "cognition_id": wf_cognition_id,
            "type": wf_cognition["type"],
        }
        results["total_injected"] += 1
        _save_history({
            "id": str(uuid.uuid4()),
            "source_type": "workflow",
            "source_id": result.workflow_id,
            "cognition_id": wf_cognition_id,
            "cognition_type": wf_cognition["type"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        })
        # 注入各任务结果
        if result.task_results:
            for task_result in result.task_results:
                task_result.workflow_id = task_result.workflow_id or result.workflow_id
                task_cognition = _generate_cognition_from_task(task_result)
                task_cognition_id = _inject_cognition(task_cognition)
                results["task_cognitions"].append({
                    "task_id": task_result.task_id,
                    "cognition_id": task_cognition_id,
                    "type": task_cognition["type"],
                })
                results["total_injected"] += 1
                _save_history({
                    "id": str(uuid.uuid4()),
                    "source_type": "task",
                    "source_id": task_result.task_id,
                    "cognition_id": task_cognition_id,
                    "cognition_type": task_cognition["type"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "success",
                })
        return results
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"注入失败: {str(e)}")

@router.post("/dispute-result", response_model=InjectResponse)
def inject_dispute_result(result: DisputeResultInput):
    """注入争议解决结果到 Grasp 知识库"""
    try:
        cognition = _generate_cognition_from_dispute(result)
        cognition_id = _inject_cognition(cognition)
        _save_history({
            "id": str(uuid.uuid4()),
            "source_type": "dispute",
            "source_id": result.dispute_id,
            "cognition_id": cognition_id,
            "cognition_type": cognition["type"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        })
        return InjectResponse(
            status="success",
            cognition_id=cognition_id,
            cognition_type=cognition["type"],
            message=f"争议解决结果已注入知识库：{cognition['type']}",
        )
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"注入失败: {str(e)}")

@router.get("/status")
def get_injection_status(
    limit: int = 50,
    source_type: Optional[str] = None,
):
    """查看注入历史记录"""
    try:
        history = _load_history()
        if source_type:
            history = [h for h in history if h.get("source_type") == source_type]
        history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {
            "status": "success",
            "total": len(history),
            "history": history[:limit],
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "total": 0, "history": []}
