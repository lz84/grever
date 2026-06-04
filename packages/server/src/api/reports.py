"""
执行报告 API

GET /api/v1/reports/{workflow_id}
返回工作流执行报告：
- 总耗时
- 任务完成率
- 冲突解决次数

数据来源：Workflow/WorkflowStep（SQLite）+ ExecutionTracker + DisputeManager
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime

from persistence.database import DatabaseManager
from persistence.base import DatabaseConfig
from persistence.repository import WorkflowRepository, WorkflowStepRepository
from persistence.tables import disputes as disputes_table
from models import WorkflowStepStatus

# Grasp 预案匹配（已废弃）

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# 全局缓存（在 server.py 中初始化后可注入）
_db_manager = None
_workflow_repo = None
_step_repo = None

def init_repos(db_manager=None, workflow_repo=None, step_repo=None):
    """初始化仓库实例（由 server.py 调用）"""
    global _db_manager, _workflow_repo, _step_repo
    _db_manager = db_manager
    _workflow_repo = workflow_repo
    _step_repo = step_repo

def _get_repos():
    """懒加载仓库"""
    global _db_manager, _workflow_repo, _step_repo
    if _workflow_repo is None:
        _db_manager = DatabaseManager(DatabaseConfig(provider="sqlite", path=r"D:\work\research\agents-nexus\data\reins.db"))
        _workflow_repo = WorkflowRepository(_db_manager.engine)
        _step_repo = WorkflowStepRepository(_db_manager.engine)
    return _workflow_repo, _step_repo, _db_manager

@router.get("/{workflow_id}")
def get_execution_report(workflow_id: str):
    """
    获取工作流执行报告
    
    返回：
    - workflow_id: 工作流 ID
    - total_time_ms: 总耗时（毫秒）
    - total_time_human: 总耗时（人类可读）
    - task_completion_rate: 任务完成率（0-100%）
    - conflict_resolution_count: 冲突解决次数
    - step_details: 步骤详情
    """
    workflow_repo, step_repo, db_manager = _get_repos()
    
    # 1. 获取工作流
    wf = workflow_repo.get_with_steps(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    steps = wf.steps or []
    
    # 2. 计算总耗时
    total_time_ms = _calc_total_time_ms(wf, steps)
    
    # 3. 计算任务完成率
    completion_rate = _calc_completion_rate(steps)
    
    # 4. 冲突解决次数（从 disputes 表查询）
    conflict_count = _count_resolved_disputes(workflow_id, db_manager)
    
    # 5. 步骤详情
    step_details = []
    for step in steps:
        step_info = {
            "id": step.id,
            "name": step.name,
            "status": step.status,
            "agent_id": step.agent_id,
            "order": step.order,
            "retry_count": step.retry_count,
            "error": step.error,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            "duration_ms": _calc_step_duration_ms(step),
        }
        step_details.append(step_info)
    
    # 7. 计算各 Agent 效率
    agent_stats = _calc_agent_stats(steps)
    
    report = {
        "workflow_id": workflow_id,
        "workflow_name": wf.name,
        "status": wf.status,
        "goal_id": wf.goal_id,
        "total_steps": len(steps),
        "total_time_ms": total_time_ms,
        "total_time_human": _format_duration(total_time_ms),
        "task_completion_rate": completion_rate,
        "conflict_resolution_count": conflict_count,
        "step_details": step_details,
        "agent_stats": agent_stats,
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "started_at": wf.started_at.isoformat() if wf.started_at else None,
        "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
    }
    
    return report

# ============================================================================
# 计算函数
# ============================================================================

def _calc_total_time_ms(wf, steps: list) -> int:
    """计算总耗时（毫秒）"""
    # 优先使用 workflow 的 started_at / completed_at
    if wf.started_at and wf.completed_at:
        delta = wf.completed_at - wf.started_at
        return int(delta.total_seconds() * 1000)
    
    # 回退：从步骤的 started_at / completed_at 推算
    all_times = []
    for step in steps:
        if step.started_at:
            all_times.append(step.started_at)
        if step.completed_at:
            all_times.append(step.completed_at)
    
    if len(all_times) >= 2:
        delta = max(all_times) - min(all_times)
        return int(delta.total_seconds() * 1000)
    
    # 回退：使用 created_at / updated_at
    if wf.created_at and wf.updated_at:
        delta = wf.updated_at - wf.created_at
        return int(delta.total_seconds() * 1000)
    
    return 0

def _calc_completion_rate(steps: list) -> float:
    """计算任务完成率（0-100）"""
    if not steps:
        return 0.0
    
    done_statuses = {
        WorkflowStepStatus.DONE,
        "done",
    }
    terminal_statuses = {
        WorkflowStepStatus.DONE,
        WorkflowStepStatus.FAILED,
        WorkflowStepStatus.SKIPPED,
        "done",
        "failed",
        "skipped",
    }
    
    completed = sum(
        1 for s in steps
        if s.status in done_statuses or str(s.status).lower() in {"done", "completed"}
    )
    
    return round((completed / len(steps)) * 100, 1)

def _count_resolved_disputes(workflow_id: str, db_manager) -> int:
    """统计已解决的冲突次数"""
    if db_manager is None:
        return 0
    
    try:
        with db_manager.engine.connect() as conn:
            # 统计 resolved 或 closed 状态的争议
            query = disputes_table.select().where(
                disputes_table.c.status.in_(["resolved", "closed"])
            )
            rows = conn.execute(query).fetchall()
            return len(rows)
    except Exception:
        return 0

def _calc_agent_stats(steps: list) -> List[Dict[str, Any]]:
    """计算各 Agent 的执行统计"""
    agent_data: Dict[str, Dict] = {}
    
    for step in steps:
        if not step.agent_id:
            continue
        
        if step.agent_id not in agent_data:
            agent_data[step.agent_id] = {
                "agent_id": step.agent_id,
                "total_tasks": 0,
                "completed": 0,
                "failed": 0,
                "total_retries": 0,
                "total_duration_ms": 0,
            }
        
        agent_data[step.agent_id]["total_tasks"] += 1
        
        if step.status in (WorkflowStepStatus.DONE, "done"):
            agent_data[step.agent_id]["completed"] += 1
        elif step.status in (WorkflowStepStatus.FAILED, "failed"):
            agent_data[step.agent_id]["failed"] += 1
        
        agent_data[step.agent_id]["total_retries"] += (step.retry_count or 0)
        agent_data[step.agent_id]["total_duration_ms"] += _calc_step_duration_ms(step)
    
    stats = list(agent_data.values())
    for s in stats:
        s["success_rate"] = round(
            (s["completed"] / s["total_tasks"] * 100) if s["total_tasks"] > 0 else 0, 1
        )
        s["avg_duration_ms"] = round(
            s["total_duration_ms"] / s["total_tasks"] if s["total_tasks"] > 0 else 0
        )
    
    return stats

def _format_duration(ms: int) -> str:
    """格式化毫秒为人类可读字符串"""
    if ms < 0:
        return "0ms"
    
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = seconds / 60
    if minutes < 60:
        m = int(minutes)
        s = int(seconds) % 60
        return f"{m}m {s}s"
    
    hours = minutes / 60
    h = int(hours)
    m = int(minutes) % 60
    return f"{h}h {m}m"
