"""人类输入 API - 查询端点（只读操作）

Sprint 91 增强：
- B91-4: pending/recent 查询支持 scenario_ref / goal_id 过滤
- 新增场景 pending 端点
"""
import json
from loguru import logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db
from reins.api.human_input_models import HumanInputRequest

router = APIRouter(tags=["human-input"])

def _row_to_human_input(row):
    """将 DB row 转为 HumanInputRequest 对象"""
    input_data = row.input_data
    if isinstance(input_data, str):
        try:
            input_data = json.loads(input_data)
        except json.JSONDecodeError:
            input_data = None
    context = row.context
    if isinstance(context, str):
        try:
            context = json.loads(context)
        except json.JSONDecodeError:
            context = None

    return HumanInputRequest(
        id=row.id,
        task_id=row.task_id,
        title=row.title,
        description=row.description,
        input_type=row.input_type,
        status=row.status,
        input_data=input_data,
        submitted_by=row.submitted_by,
        submitted_at=str(row.submitted_at) if row.submitted_at else None,
        created_at=str(row.created_at) if row.created_at else None,
        updated_at=str(row.updated_at) if row.updated_at else None,
        context=context
    )

@router.get("/pending")
def get_pending_requests(
    scenario_ref: Optional[str] = Query(None, description="按场景ID过滤"),
    goal_id: Optional[str] = Query(None, description="按目标ID过滤"),
    db: Session = Depends(get_db)
):
    """
    查询所有待处理的人类输入请求

    GET /api/v1/human-input/pending?[scenario_ref=xxx][&goal_id=xxx]

    Sprint 91: 支持 scenario_ref / goal_id 可选过滤
    """
    from reins.api.human_input_models import PendingHumanInputResponse

    try:
        # 构建过滤条件
        conditions = ["status = 'pending'"]
        params: dict = {}

        if scenario_ref:
            conditions.append("scenario_ref = :scenario_ref")
            params["scenario_ref"] = scenario_ref

        if goal_id:
            conditions.append("goal_id = :goal_id")
            params["goal_id"] = goal_id

        where_clause = " AND ".join(conditions)

        result = db.execute(text(f"""
            SELECT id, task_id, title, description, input_type, status,
                   input_data, submitted_by, submitted_at, created_at, updated_at, context
            FROM human_input_requests
            WHERE {where_clause}
            ORDER BY created_at DESC
        """), params).fetchall()

        pending_requests = [_row_to_human_input(row) for row in result]

        return PendingHumanInputResponse(
            requests=pending_requests,
            total=len(pending_requests)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询待处理请求失败: {str(e)}")

@router.get("/scenario/{scenario_id}/pending")
def get_scenario_pending_requests(scenario_id: str, db: Session = Depends(get_db)):
    """
    查询特定场景下待处理的人类输入请求

    GET /api/v1/human-input/scenario/{scenario_id}/pending

    Sprint 91 新增
    """
    try:
        result = db.execute(text("""
            SELECT id, task_id, title, description, input_type, status,
                   input_data, submitted_by, submitted_at, created_at, updated_at, context,
                   executor_type, required_role, assigned_to
            FROM human_input_requests
            WHERE scenario_ref = :scenario_id AND status = 'pending'
            ORDER BY created_at DESC
        """), {"scenario_id": scenario_id}).fetchall()

        requests = []
        for row in result:
            req = _row_to_human_input(row)
            # 附加 executor_type 和权限信息
            requests.append({
                **req.model_dump(),
                "executor_type": row.executor_type if row.executor_type else 'ai_approval',
                "required_role": row.required_role,
                "assigned_to": row.assigned_to,
            })

        return {
            "scenario_id": scenario_id,
            "requests": requests,
            "total": len(requests)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询场景待处理请求失败: {str(e)}")

@router.get("/recent")
def get_recent_requests(
    limit: int = 10,
    scenario_ref: Optional[str] = Query(None, description="按场景ID过滤"),
    goal_id: Optional[str] = Query(None, description="按目标ID过滤"),
    db: Session = Depends(get_db)
):
    """
    获取最近的人类输入请求

    GET /api/v1/human-input/recent?limit=10[&scenario_ref=xxx][&goal_id=xxx]

    Sprint 91: 支持 scenario_ref / goal_id 可选过滤
    """
    try:
        conditions = ["1=1"]
        params: dict = {"limit": limit}

        if scenario_ref:
            conditions.append("scenario_ref = :scenario_ref")
            params["scenario_ref"] = scenario_ref

        if goal_id:
            conditions.append("goal_id = :goal_id")
            params["goal_id"] = goal_id

        where_clause = " AND ".join(conditions)

        result = db.execute(text(f"""
            SELECT id, task_id, title, description, input_type, status,
                   input_data, submitted_by, submitted_at, created_at, updated_at, context
            FROM human_input_requests
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """), params).fetchall()

        recent = [_row_to_human_input(row) for row in result]

        return recent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最近请求失败: {str(e)}")
@router.get("/task/{task_id}")
def get_human_inputs_for_task(task_id: str, db: Session = Depends(get_db)):
    """
    获取特定任务的人类输入请求
    GET /api/v1/human-input/task/{task_id}
    """
    try:
        result = db.execute(text("""
            SELECT id, task_id, title, description, input_type, status,
                   input_data, submitted_by, submitted_at, created_at, updated_at, context
            FROM human_input_requests
            WHERE task_id = :task_id
            ORDER BY created_at DESC
        """), {"task_id": task_id}).fetchall()

        task_requests = []
        for row in result:
            task_requests.append(HumanInputRequest(
                id=row.id,
                task_id=row.task_id,
                title=row.title,
                description=row.description,
                input_type=row.input_type,
                status=row.status,
                input_data=row.input_data,
                submitted_by=row.submitted_by,
                submitted_at=str(row.submitted_at) if row.submitted_at else None,
                created_at=str(row.created_at) if row.created_at else None,
                updated_at=str(row.updated_at) if row.updated_at else None,
                context=row.context
            ))

        return {
            "task_id": task_id,
            "requests": task_requests,
            "total": len(task_requests)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务相关请求失败: {str(e)}")

@router.get("/{input_id}")
def get_human_input_details(input_id: str, db: Session = Depends(get_db)):
    """
    获取人类输入请求详情
    GET /api/v1/human-input/{input_id}
    """
    try:
        result = db.execute(text("""
            SELECT id, task_id, title, description, input_type, status,
                   input_data, submitted_by, submitted_at, created_at, updated_at, context
            FROM human_input_requests
            WHERE id = :input_id
        """), {"input_id": input_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"人类输入请求 {input_id} 不存在")

        input_data = result.input_data
        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except json.JSONDecodeError:
                input_data = None
        context = result.context
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except json.JSONDecodeError:
                context = None

        return HumanInputRequest(
            id=result.id,
            task_id=result.task_id,
            title=result.title,
            description=result.description,
            input_type=result.input_type,
            status=result.status,
            input_data=input_data,
            submitted_by=result.submitted_by,
            submitted_at=str(result.submitted_at) if result.submitted_at else None,
            created_at=str(result.created_at) if result.created_at else None,
            updated_at=str(result.updated_at) if result.updated_at else None,
            context=context
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取请求详情失败: {str(e)}")

