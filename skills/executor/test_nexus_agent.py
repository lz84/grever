"""
Tests for Nexus Agent Skill.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trigger import NexusTaskTrigger
from executor import NexusTaskExecutor, TaskContext


class TestNexusTaskTrigger:
    """测试 Trigger 模块"""
    
    @patch("trigger.requests.post")
    def test_check_assigned_tasks_success(self, mock_post):
        """测试成功获取任务"""
        # 模拟 API 响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "agent_id": "test-agent",
            "assigned_tasks": [
                {
                    "id": "task-001",
                    "title": "Test Task",
                    "description": "Test description",
                    "priority": "high",
                    "context": {}
                }
            ],
            "load_limit_warning": False
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        trigger = NexusTaskTrigger(
            nexus_url="http://test:8000",
            agent_id="test-agent"
        )
        
        result = trigger.check_assigned_tasks()
        
        assert result["success"] is True
        assert len(result["assigned_tasks"]) == 1
        assert result["assigned_tasks"][0]["id"] == "task-001"
    
    @patch("trigger.requests.post")
    def test_check_assigned_tasks_no_tasks(self, mock_post):
        """测试没有新任务"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "assigned_tasks": [],
            "load_limit_warning": False
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        trigger = NexusTaskTrigger()
        
        result = trigger.check_assigned_tasks()
        
        assert result["success"] is True
        assert len(result["assigned_tasks"]) == 0
    
    def test_has_new_tasks(self):
        """测试 has_new_tasks 方法"""
        with patch.object(NexusTaskTrigger, 'check_assigned_tasks') as mock_check:
            # 有任务
            mock_check.return_value = {"assigned_tasks": [{"id": "task-001"}]}
            trigger = NexusTaskTrigger()
            assert trigger.has_new_tasks() is True
            
            # 无任务
            mock_check.return_value = {"assigned_tasks": []}
            assert trigger.has_new_tasks() is False


class TestNexusTaskExecutor:
    """测试 Executor 模块"""
    
    @patch("executor.requests.get")
    def test_get_task_context_success(self, mock_get):
        """测试成功获取任务上下文"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "task_id": "task-001",
            "context": {
                "scenario_guide": {
                    "name": "Scenario 1",
                    "description": "Test scenario",
                    "steps": []
                },
                "related_files": ["file1.py"],
                "previous_attempts": [],
                "goal_info": {"id": "goal-001"}
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        executor = NexusTaskExecutor()
        context = executor.get_task_context("task-001")
        
        assert context is not None
        assert context.task_id == "task-001"
        assert context.scenario_guide is not None
    
    def test_execute_task(self):
        """测试任务执行"""
        context = TaskContext(
            task_id="task-001",
            title="Test Task",
            description="Test",
            priority="medium"
        )
        
        executor = NexusTaskExecutor()
        result = executor.execute_task(context)
        
        assert result["status"] == "done"
        assert "executed successfully" in result["result"]
    
    @patch("executor.requests.post")
    def test_report_complete_success(self, mock_post):
        """测试成功上报完成"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "task_id": "task-001"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        executor = NexusTaskExecutor()
        result = executor.report_complete("task-001", {
            "status": "done",
            "result": "Success"
        })
        
        assert result["success"] is True
    
    @patch("executor.requests.post")
    def test_execute_single_task_success(self, mock_post):
        """测试完整任务执行流程（成功）"""
        # Mock get_task_context
        mock_context = TaskContext(
            task_id="task-001",
            title="Test Task",
            description="Test",
            priority="medium"
        )
        
        # Mock responses
        mock_get_response = Mock()
        mock_get_response.json.return_value = {
            "success": True,
            "task_id": "task-001",
            "context": {
                "scenario_guide": {},
                "related_files": [],
                "previous_attempts": [],
                "goal_info": {}
            }
        }
        mock_get_response.raise_for_status.return_value = None
        
        mock_post_complete = Mock()
        mock_post_complete.json.return_value = {
            "success": True,
            "task_id": "task-001"
        }
        mock_post_complete.raise_for_status.return_value = None
        
        with patch("executor.requests.get", return_value=mock_get_response):
            with patch("executor.requests.post", return_value=mock_post_complete):
                executor = NexusTaskExecutor()
                task = {"id": "task-001", "title": "Test"}
                result = executor.execute_single_task(task)
                
                assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
