# -*- coding: utf-8 -*-
"""
Project API Unit Tests

MAK-212: Project 数据模型 + CRUD API 测试
"""

import pytest
import sys
import os

# 添加源目录到路径
src_dir = os.path.join(os.path.dirname(__file__), '..', '..')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


class TestProjectModel:
    """Project 模型单元测试"""

    def test_project_schema_fields(self):
        """Project schema 字段验证"""
        from datetime import datetime
        from models.project import ProjectCreate, ProjectUpdate, ProjectResponse
        
        # ProjectCreate
        project_create = ProjectCreate(
            name="测试项目",
            description="测试描述",
            status="active",
            goal_id=1
        )
        assert project_create.name == "测试项目"
        assert project_create.description == "测试描述"
        assert project_create.status == "active"
        assert project_create.goal_id == 1
        
        # ProjectUpdate
        project_update = ProjectUpdate(
            name="更新后的项目",
            description="更新描述",
            status="inactive",
            goal_id=2
        )
        assert project_update.name == "更新后的项目"
        assert project_update.status == "inactive"
        assert project_update.goal_id == 2
        
        # ProjectResponse
        project_response = ProjectResponse(
            id=1,
            name="测试项目",
            description="测试描述",
            goal_id=1,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert project_response.id == 1
        assert project_response.goal_id == 1
        assert project_response.status == "active"

    def test_project_model_fields(self):
        """Project 模型字段验证"""
        from datetime import datetime
        from models.project import Project
        
        project = Project(
            name="测试项目",
            description="测试描述",
            status="active",
            goal_id=1
        )
        assert project.name == "测试项目"
        assert project.description == "测试描述"
        assert project.status == "active"
        assert project.goal_id == 1


class TestGoalModel:
    """Goal 模型测试"""

    def test_goal_schema_with_goal_id(self):
        """Goal schema 包含 goal_id 字段"""
        from datetime import datetime
        from reins.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
        
        # GoalCreate
        goal_create = GoalCreate(
            title="测试目标",
            description="测试描述",
            status="draft",
            project_id=1,
            goal_id=2,
            parent_id=None
        )
        assert goal_create.goal_id == 2
        
        # GoalUpdate
        goal_update = GoalUpdate(
            title="更新后的目标",
            status="planned",
            goal_id=3
        )
        assert goal_update.goal_id == 3
        
        # GoalResponse
        goal_response = GoalResponse(
            id="goal-001",
            title="测试目标",
            description="测试描述",
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            goal_id=1
        )
        assert goal_response.goal_id == 1

    def test_project_to_dict_with_goal_id(self):
        """Project.to_dict() 包含 goal_id"""
        from datetime import datetime
        from models.project import Project
        
        project = Project(
            id=1,
            name="测试项目",
            description="测试描述",
            goal_id=1,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        project_dict = project.to_dict()
        
        assert project_dict['id'] == 1
        assert project_dict['name'] == "测试项目"
        assert project_dict['goal_id'] == 1
        assert project_dict['status'] == "active"
        assert 'created_at' in project_dict
        assert 'updated_at' in project_dict


class TestAPIRoutes:
    """API 路由测试"""

    def test_projects_router_has_goal_id_param(self):
        """Project API 路由支持 goal_id 过滤"""
        from fastapi import Query
        from reins.api.projects import list_projects
        
        # 检查函数签名中是否有 goal_id 参数
        import inspect
        sig = inspect.signature(list_projects)
        params = sig.parameters
        
        assert 'goal_id' in params
        assert params['goal_id'].default is None


class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_project_without_goal_id(self):
        """Project 可以没有 goal_id（向后兼容）"""
        from datetime import datetime
        from models.project import ProjectResponse
        
        project = ProjectResponse(
            id=1,
            name="测试项目",
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert project.goal_id is None

    def test_goal_response_without_goal_id(self):
        """GoalResponse 可以没有 goal_id"""
        from datetime import datetime
        from reins.schemas.goal import GoalResponse
        
        goal = GoalResponse(
            id="goal-001",
            title="测试目标",
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert goal.goal_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
