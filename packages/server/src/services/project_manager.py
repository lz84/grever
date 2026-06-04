"""
项目管理 (Project Management)
负责项目的创建、成员管理、进度跟踪

2026-04-25 精简：删除内存字典，不再被 ReinsServer 使用。
保留类定义以兼容旧代码，所有方法已废弃。
"""

from typing import List, Optional
from models import Project, ProjectStatus

class ProjectManager:
    """
    项目管理器（已废弃）

    2026-04-25 重构：Project CRUD 全部走 DB repository。
    此类保留仅用于向后兼容，内部方法不再操作内存字典。
    """

    def __init__(self):
        pass  # 不再维护 _projects 内存字典
