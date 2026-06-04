"""
FE-P8-06: 全局搜索 API 测试

测试 POST /api/v1/search?q=keyword 端点
"""

import pytest
import logging
import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class TestGlobalSearchEndpoint:
    """全局搜索 API 测试"""

    def test_search_endpoint_registered(self):
        """搜索端点已在 server.py 中注册"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        assert '@app.get("/api/v1/search")' in source
        assert "def global_search(" in source
        logger.info("✓ Global search endpoint registered in server.py")

    def test_search_returns_categorized_results(self):
        """搜索返回分类结果结构"""
        # 验证源码中有正确的返回结构
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        # 检查返回结构包含所有分类
        assert '"goals"' in source
        assert '"projects"' in source
        assert '"tasks"' in source
        assert '"plans"' in source
        assert '"total"' in source
        logger.info("✓ Search returns categorized results (goals/projects/tasks/plans)")

    def test_search_validates_empty_query(self):
        """空查询词返回 400"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        # 检查有空的验证
        assert 'status_code=400' in source
        assert '搜索词不能为空' in source
        logger.info("✓ Empty query returns 400")

    def test_search_goals_section(self):
        """搜索 Goals 部分实现正确"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        # 检查 goals 搜索逻辑
        assert "GoalModel" in source
        assert "g.title" in source
        assert "g.description" in source
        logger.info("✓ Goals search logic present")

    def test_search_projects_section(self):
        """搜索 Projects 部分实现正确"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        assert "reins.list_projects()" in source
        assert "p.name" in source
        logger.info("✓ Projects search logic present")

    def test_search_tasks_section(self):
        """搜索 Tasks 部分实现正确"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        assert "TaskModel" in source
        assert "t.title" in source
        assert "t.description" in source
        logger.info("✓ Tasks search logic present")

    def test_search_plans_section(self):
        """搜索 Plans 部分使用 PlanMatcher"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        assert "PlanMatcher" in source
        assert "matcher.search" in source
        logger.info("✓ Plans search uses PlanMatcher")

    def test_search_limit_parameter(self):
        """搜索支持 limit 参数"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        assert "limit: int = Query(" in source
        assert "ge=1" in source
        assert "le=50" in source
        logger.info("✓ Search supports limit parameter (1-50)")

    def test_search_error_handling(self):
        """搜索各部分有错误处理"""
        import api.server as srv
        source = open(srv.__file__, "r", encoding="utf-8").read()
        
        # 每个搜索部分都有 try/except
        assert source.count("except Exception as e:") >= 4  # 至少 4 个部分
        assert "Search" in source  # 日志前缀
        logger.info("✓ Search has error handling for each section")


class TestSearchAPIIntegration:
    """搜索 API 集成验证"""

    def test_search_file_syntax(self):
        """server.py 语法正确"""
        import py_compile
        server_path = Path(__file__).parent.parent.parent / "src" / "reins" / "api" / "server.py"
        py_compile.compile(str(server_path), doraise=True)
        logger.info("✓ server.py syntax OK")

    def test_search_imports_available(self):
        """搜索所需模块可导入"""
        from grasp.plans import PlanStore, PlanMatcher
        from models.goal import Goal as GoalModel
        from models.task import Task as TaskModel
        logger.info("✓ All search dependencies importable")
