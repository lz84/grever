"""Human Review API: batch ruling endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from reins.common.database import get_db
from .human_review_logic import _process_task_ruling, _process_human_input_ruling
from .human_review_models import (
    BatchRulingRequest,
    BatchRulingResponse,
    BatchRulingResult,
)

router = APIRouter()

@router.post("/batch-ruling", response_model=BatchRulingResponse)
def batch_ruling(request: BatchRulingRequest, db: Session = Depends(get_db)):
    """批量裁决"""
    try:
        results = []
        success_count = 0
        failed_count = 0

        for item in request.items:
            try:
                ruling_text = request.global_ruling if request.global_ruling else item.ruling
                if item.type in ["task", "disputed", "waiting", "waiting_human"]:
                    result = _process_task_ruling(db, item.id, ruling_text, item.action)
                elif item.type in ["human_input", "assist", "pending_assist"]:
                    result = _process_human_input_ruling(db, item.id, ruling_text, item.action)
                else:
                    raise ValueError(f"未知类型: {item.type}")

                result_obj = BatchRulingResult(
                    id=item.id, type=item.type, success=True,
                    message=result.get("message", f"Successfully ruled {item.id}"),
                    new_status=result.get("new_status"), error=None
                )
                success_count += 1
            except Exception as e:
                result_obj = BatchRulingResult(
                    id=item.id, type=item.type, success=False,
                    message=f"Failed to rule {item.id}", new_status=None, error=str(e)
                )
                failed_count += 1
            results.append(result_obj)

        return BatchRulingResponse(success_count=success_count, failed_count=failed_count, results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量裁决失败: {str(e)}")
