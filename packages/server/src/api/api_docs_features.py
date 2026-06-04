"""API Documentation: features listing"""
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/features", response_model=Dict[str, Any])
def get_api_features():
    """
    获取API功能特性
    返回系统支持的主要功能特性
    """
    features = {
        "goal_id": "goal-cb4c76143b4c",
        "title": "Nexus Backend API Features",
        "description": "Nexus平台后端API功能特性汇总",
        "features": {
            "task_management": {
                "title": "任务管理",
                "description": "完整的任务创建、更新、完成、失败处理流程",
                "capabilities": [
                    "任务依赖管理",
                    "任务状态跟踪",
                    "任务验证器继承",
                    "任务超时处理",
                    "人类输入集成"
                ]
            },
            "human_input_system": {
                "title": "人类输入系统",
                "description": "支持任务需要人类输入的完整工作流",
                "capabilities": [
                    "人类输入请求创建",
                    "人类输入提交/拒绝",
                    "依赖任务解锁",
                    "等待人类输入状态",
                    "飞书通知集成"
                ]
            },
            "verification_system": {
                "title": "验证系统",
                "description": "三层验证器继承机制",
                "capabilities": [
                    "任务级验证器",
                    "项目级验证器",
                    "目标级验证器",
                    "验证器继承",
                    "验收标准验证"
                ]
            },
            "timeout_handling": {
                "title": "超时处理",
                "description": "自动检测和处理超时任务",
                "capabilities": [
                    "任务超时检测",
                    "自动状态更新",
                    "通知机制",
                    "定期扫描",
                    "手动触发检查"
                ]
            },
            "dependency_resolution": {
                "title": "依赖解析",
                "description": "处理任务依赖关系的系统",
                "capabilities": [
                    "前置依赖管理",
                    "任务解锁机制",
                    "人类输入依赖解锁",
                    "依赖状态跟踪"
                ]
            },
            "workflow_management": {
                "title": "工作流管理",
                "description": "工作流创建和执行管理系统",
                "capabilities": [
                    "工作流定义",
                    "工作流执行",
                    "节点依赖管理",
                    "状态跟踪"
                ]
            },
            "integration_features": {
                "title": "集成特性",
                "description": "与其他系统和服务的集成",
                "capabilities": [
                    "飞书通知服务",
                    "前端API端点",
                    "数据库持久化",
                    "事件总线集成"
                ]
            }
        },
        "api_version": "v1",
        "status": "production"
    }

    return features
