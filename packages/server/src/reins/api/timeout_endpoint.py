"""
超时处理API端点

提供手动触发超时检查的API端点
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from services.timeout_handler import handle_timeouts, get_timeout_handler

router = APIRouter(prefix="/api/v1/timeout", tags=["timeout"])

class TimeoutCheckResponse(BaseModel):
    """超时检查响应模型"""
    success: bool
    message: str
    processed_count: int
    notified_count: int
    errors_count: int
    processed_tasks: list
    notified_tasks: list
    errors: list

class TimeoutConfigResponse(BaseModel):
    """超时配置响应模型"""
    default_timeout_hours: int
    status_to_monitor: str
    target_status_on_timeout: str
    message: str

@router.post("/check", response_model=TimeoutCheckResponse)
def manual_timeout_check():
    """
    手动触发超时检查
    
    执行一次完整的超时任务扫描和处理
    """
    try:
        logger.info("手动触发超时检查")
        result = handle_timeouts()
        
        response = TimeoutCheckResponse(
            success=True,
            message="超时检查完成",
            processed_count=result.get("processed_count", 0),
            notified_count=result.get("notified_count", 0),
            errors_count=result.get("errors_count", 0),
            processed_tasks=result.get("processed_tasks", []),
            notified_tasks=result.get("notified_tasks", []),
            errors=result.get("errors", [])
        )
        
        logger.info(f"手动超时检查完成: {response.processed_count} 个任务被处理")
        return response
        
    except Exception as e:
        logger.error(f"手动超时检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"超时检查失败: {str(e)}"
        )

@router.get("/config", response_model=TimeoutConfigResponse)
def get_timeout_config():
    """
    获取超时配置信息
    
    返回当前的超时配置参数
    """
    try:
        handler = get_timeout_handler()
        config = handler.get_timeout_config()
        
        response = TimeoutConfigResponse(
            default_timeout_hours=config["default_timeout_hours"],
            status_to_monitor=config["status_to_monitor"],
            target_status_on_timeout=config["target_status_on_timeout"],
            message="超时配置获取成功"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"获取超时配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )

@router.post("/check-task/{task_id}")
def check_single_task_timeout(task_id: str):
    """
    检查单个任务是否超时
    
    Args:
        task_id: 任务ID
        
    Returns:
        dict: 包含检查结果的字典
    """
    try:
        from services.timeout_handler import is_task_timed_out
        
        is_timed_out = is_task_timed_out(task_id)
        
        return {
            "task_id": task_id,
            "is_timed_out": is_timed_out,
            "message": f"任务 {task_id} 超时检查完成"
        }
        
    except Exception as e:
        logger.error(f"检查任务超时状态失败 for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查任务超时状态失败: {str(e)}"
        )

logger.info("Timeout API endpoints loaded")