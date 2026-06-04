"""API Documentation: endpoint listing & status"""
from loguru import logger

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()

class APIEndpoint(BaseModel):
    """API端点信息模型"""
    path: str
    method: str
    summary: str
    description: str
    tags: List[str]

class APIDocumentationResponse(BaseModel):
    """API文档响应模型"""
    endpoints: List[APIEndpoint]
    total_endpoints: int
    api_version: str
    goal_id: str

@router.get("/endpoints", response_model=APIDocumentationResponse)
def get_api_endpoints():
    """
    获取所有API端点信息
    返回系统中所有可用的API端点列表
    """
    endpoints = [
        # 任务相关API
        APIEndpoint(
            path="/api/v1/tasks",
            method="GET",
            summary="获取任务列表",
            description="获取系统中的所有任务，支持过滤和分页",
            tags=["tasks"]
        ),
        APIEndpoint(
            path="/api/v1/tasks",
            method="POST",
            summary="创建任务",
            description="创建新任务，支持设置依赖关系",
            tags=["tasks"]
        ),
        APIEndpoint(
            path="/api/v1/tasks/{task_id}/complete",
            method="POST",
            summary="完成任务",
            description="将任务标记为完成，支持验证和人类输入需求检测",
            tags=["tasks"]
        ),
        APIEndpoint(
            path="/api/v1/tasks/{task_id}/fail",
            method="POST",
            summary="标记任务失败",
            description="将任务标记为失败，支持重试机制",
            tags=["tasks"]
        ),

        # 目标相关API
        APIEndpoint(
            path="/api/v1/goals",
            method="GET",
            summary="获取目标列表",
            description="获取系统中的所有目标",
            tags=["goals"]
        ),
        APIEndpoint(
            path="/api/v1/goals",
            method="POST",
            summary="创建目标",
            description="创建新目标，支持设置验证器",
            tags=["goals"]
        ),

        # 项目相关API
        APIEndpoint(
            path="/api/v1/projects",
            method="GET",
            summary="获取项目列表",
            description="获取系统中的所有项目",
            tags=["projects"]
        ),
        APIEndpoint(
            path="/api/v1/projects",
            method="POST",
            summary="创建项目",
            description="创建新项目，支持设置验证器",
            tags=["projects"]
        ),

        # 人类输入API
        APIEndpoint(
            path="/api/v1/human-input/pending",
            method="GET",
            summary="获取待处理人类输入请求",
            description="获取所有待处理的人类输入请求",
            tags=["human-input"]
        ),
        APIEndpoint(
            path="/api/v1/human-input/{input_id}/submit",
            method="POST",
            summary="提交人类输入",
            description="提交人类输入结果，解锁依赖任务",
            tags=["human-input"]
        ),
        APIEndpoint(
            path="/api/v1/human-input/{input_id}/reject",
            method="POST",
            summary="拒绝人类输入",
            description="拒绝人类输入请求",
            tags=["human-input"]
        ),

        # 超时处理API
        APIEndpoint(
            path="/api/v1/timeout/check",
            method="POST",
            summary="手动触发超时检查",
            description="手动检查并处理超时的任务",
            tags=["timeout"]
        ),
        APIEndpoint(
            path="/api/v1/timeout/config",
            method="GET",
            summary="获取超时配置",
            description="获取当前的超时配置信息",
            tags=["timeout"]
        ),

        # 工作流API
        APIEndpoint(
            path="/api/v1/workflows",
            method="GET",
            summary="获取工作流列表",
            description="获取系统中的所有工作流",
            tags=["workflows"]
        ),
        APIEndpoint(
            path="/api/v1/workflows/from-goal/{goal_id}",
            method="POST",
            summary="从目标创建工作流",
            description="基于目标自动创建工作流",
            tags=["workflows"]
        ),

        # 场景API
        APIEndpoint(
            path="/api/v1/scenarios",
            method="GET",
            summary="获取场景列表",
            description="获取所有可用的场景",
            tags=["scenarios"]
        ),
        APIEndpoint(
            path="/api/v1/scenarios/match-for-goal/{goal_id}",
            method="POST",
            summary="为目标匹配场景",
            description="为指定目标匹配最适合的场景",
            tags=["scenarios"]
        ),

        # 安全API
        APIEndpoint(
            path="/api/v1/security/verify-token",
            method="POST",
            summary="验证令牌",
            description="验证提供的安全令牌",
            tags=["security"]
        )
    ]

    return APIDocumentationResponse(
        endpoints=endpoints,
        total_endpoints=len(endpoints),
        api_version="v1",
        goal_id="goal-cb4c76143b4c"
    )

@router.get("/status", response_model=Dict[str, Any])
def get_api_status():
    """
    获取API状态
    返回API服务的当前状态
    """
    status_info = {
        "goal_id": "goal-cb4c76143b4c",
        "api_status": "operational",
        "version": "1.0.0",
        "uptime": "running",
        "endpoints_count": 50,
        "last_updated": "2026-05-04T18:30:00Z",
        "features_enabled": [
            "task_management",
            "human_input",
            "verification_inheritance",
            "timeout_handling",
            "dependency_resolution",
            "workflow_management",
            "feishu_notifications"
        ],
        "documentation_available": True
    }

    return status_info

logger.info("[API] Documentation endpoints loaded successfully")
