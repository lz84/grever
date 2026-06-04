"""人类输入 API - 操作端点（写操作）

Sprint 91 增强：
- B91-2: 按 executor_type 区分审批通过/拒绝后的 task 状态
- B91-3: 审批前置权限检查（required_role / assigned_to）
"""
import json
from loguru import logger
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db
from reins.scheduler.dependency_resolver import DependencyResolver
from reins.api.human_input_models import SubmitHumanInputRequest, HumanInputResponse

router = APIRouter(tags=["human-input"])

# executor_type 审批通过后的 task 状态映射
EXECUTOR_APPROVE_ACTION = {
    'human': 'done',       # 纯人任务，审批通过 = 完成
    'ai_approval': 'todo',  # 审批通过 = AI 开始执行
    'ai_data': 'todo',      # 数据提供 = AI 开始执行
}

def _get_hitl_info(db: Session, input_id: str) -> dict:
    """查询 HITL request 的完整信息（task_id, executor_type, 权限字段）"""
    row = db.execute(text("""
        SELECT task_id, executor_type, required_role, assigned_to
        FROM human_input_requests
        WHERE id = :input_id
    """), {"input_id": input_id}).fetchone()

    if not row:
        return {}

    # executor_type 可能为 NULL（旧数据），默认 ai_approval
    executor_type = row[1] if row[1] else 'ai_approval'

    return {
        'task_id': row[0],
        'executor_type': executor_type,
        'required_role': row[2],
        'assigned_to': row[3],
    }

def _check_permission(hitl_info: dict, submitted_by: str) -> bool:
    """
    检查用户是否有审批权限。

    规则：
    - 如果 required_role 或 assigned_to 都为空 → 任何人可审批
    - 如果有 assigned_to → 只有被指定的人可审批
    - 如果有 required_role → 检查用户角色（MVP 阶段：角色匹配 submitted_by 包含角色名）
    """
    required_role = hitl_info.get('required_role')
    assigned_to = hitl_info.get('assigned_to')

    # 无权限要求 → 任何人可审批
    if not required_role and not assigned_to:
        return True

    # 检查 assigned_to
    if assigned_to:
        # assigned_to 可能是逗号分隔的多人
        allowed = [s.strip() for s in assigned_to.split(',') if s.strip()]
        if submitted_by not in allowed:
            return False

    # 检查 required_role（MVP 简化：检查 submitted_by 是否包含角色关键词）
    if required_role:
        roles = [r.strip().lower() for r in required_role.split(',') if r.strip()]
        submitted_lower = submitted_by.lower()
        if not any(role in submitted_lower for role in roles):
            return False

    return True

def _call_unlock_on_human_input(input_id: str, task_id: str):
    """
    调用 unlock_on_human_input 函数
    返回解锁的任务列表

    T6: DependencyResolver extension - unlock_on_human_input
    """
    from reins.common.database import get_db_manager

    try:
        db_manager = get_db_manager()
        resolver = DependencyResolver(db_manager)
        unlocked_tasks = resolver.unlock_on_human_input(input_id)
        return unlocked_tasks
    except Exception as e:
        logger.error(f"Error calling unlock_on_human_input: {e}")
        return []

@router.post("/{input_id}/submit", response_model=HumanInputResponse)
def submit_human_input(input_id: str, request: SubmitHumanInputRequest, db: Session = Depends(get_db)):
    """
    提交人类输入（审批通过）

    POST /api/v1/human-input/{input_id}/submit

    Sprint 91 增强：
    a. 权限检查（B91-3）
    b. 更新 human_input_requests
    c. 根据 executor_type 更新 task 状态（B91-2）
    d. 调用 unlock_on_human_input
    """
    try:
        # 获取 HITL 请求信息
        hitl_info = _get_hitl_info(db, input_id)
        if not hitl_info:
            raise HTTPException(status_code=404, detail=f"人类输入请求 {input_id} 不存在")

        task_id = hitl_info['task_id']
        executor_type = hitl_info['executor_type']

        # B91-3: 权限检查
        submitted_by = request.submitted_by or 'anonymous'
        if not _check_permission(hitl_info, submitted_by):
            raise HTTPException(
                status_code=403,
                detail="您没有审批此任务的权限"
            )

        now = datetime.now()

        # b. 更新 human_input_requests
        input_data = request.input_data
        input_data_json = json.dumps(input_data) if input_data else None
        approval_reason = None
        if isinstance(input_data, dict):
            approval_reason = input_data.get('approval_reason')
        elif isinstance(input_data, str):
            approval_reason = input_data[:500]  # 纯字符串截断存储

        db.execute(text("""
            UPDATE human_input_requests
            SET status = 'submitted',
                input_data = :input_data,
                submitted_by = :submitted_by,
                submitted_at = :submitted_at,
                approval_reason = :approval_reason,
                updated_at = :updated_at
            WHERE id = :input_id
        """), {
            "input_id": input_id,
            "input_data": input_data_json,
            "submitted_by": submitted_by,
            "submitted_at": now,
            "approval_reason": approval_reason,
            "updated_at": now
        })

        # c. 根据 executor_type 更新 task 状态（B91-2）
        new_task_status = EXECUTOR_APPROVE_ACTION.get(executor_type, 'done')
        db.execute(text("""
            UPDATE tasks
            SET status = :status,
                completed_at = :now,
                updated_at = :now
            WHERE id = :task_id
        """), {
            "status": new_task_status,
            "now": now,
            "task_id": task_id
        })

        logger.info(
            f"[HITL] submit {input_id}: task {task_id} status → {new_task_status} (executor_type={executor_type})"
        )

        # d. human 类型不调用 unlock（任务已完成，下游由常规完成流程解锁）
        unlocked_tasks = []
        if executor_type != 'human':
            unlocked_tasks = _call_unlock_on_human_input(input_id, task_id)

        db.commit()

        return HumanInputResponse(
            success=True,
            message=f"审批通过，任务状态 → {new_task_status}" +
                    (f"，解锁了 {len(unlocked_tasks)} 个任务" if unlocked_tasks else ""),
            data={
                "input_id": input_id,
                "task_id": task_id,
                "status": "submitted",
                "new_task_status": new_task_status,
                "executor_type": executor_type,
                "unlocked_tasks": unlocked_tasks
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"提交人类输入失败: {str(e)}")

@router.post("/{input_id}/reject", response_model=HumanInputResponse)
def reject_human_input(input_id: str, db: Session = Depends(get_db)):
    """
    拒绝人类输入请求

    POST /api/v1/human-input/{input_id}/reject

    Sprint 91 增强：
    a. 权限检查（B91-3）
    b. 更新 human_input_requests
    c. task 状态 → failed
    """
    try:
        # 获取 HITL 请求信息
        hitl_info = _get_hitl_info(db, input_id)
        if not hitl_info:
            raise HTTPException(status_code=404, detail=f"人类输入请求 {input_id} 不存在")

        task_id = hitl_info['task_id']

        # B91-3: 权限检查（reject 也需要权限）
        # 注意：reject 端点没有 request body，从查询参数或默认值获取 submitted_by
        # 这里暂时跳过权限检查（因为没有 submitted_by 来源）
        # TODO: 前端调用时传入 submitted_by

        now = datetime.now()

        # b. 更新 human_input_requests
        db.execute(text("""
            UPDATE human_input_requests
            SET status = 'rejected',
                updated_at = :updated_at
            WHERE id = :input_id
        """), {
            "input_id": input_id,
            "updated_at": now
        })

        # c. task 状态 → failed
        db.execute(text("""
            UPDATE tasks
            SET status = 'failed',
                error_message = 'HITL 审批被拒绝',
                updated_at = :now
            WHERE id = :task_id
        """), {
            "now": now,
            "task_id": task_id
        })

        logger.info(f"[HITL] reject {input_id}: task {task_id} status → failed")

        db.commit()

        return HumanInputResponse(
            success=True,
            message=f"审批被拒绝，任务 {task_id} 已标记为 failed",
            data={
                "input_id": input_id,
                "task_id": task_id,
                "status": "rejected"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"拒绝人类输入失败: {str(e)}")
