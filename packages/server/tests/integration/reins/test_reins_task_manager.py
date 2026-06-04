"""
Reins Backend 单元测试
测试 TaskManager 的 create/update/delete/list_tasks 功能
测试任务状态流转
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from reins.scheduler.assigner import TaskManager
from models import TaskStatus, Priority


class TestTaskManagerCreate(unittest.TestCase):
    """测试 create_task 功能"""

    def setUp(self):
        self.manager = TaskManager()

    def test_create_task_basic(self):
        """创建基础任务"""
        task = self.manager.create_task(
            title="测试任务",
            description="这是一个测试任务",
            priority=Priority.P1,
        )
        self.assertIsNotNone(task.id)
        self.assertTrue(task.id.startswith("task-"))
        self.assertEqual(task.title, "测试任务")
        self.assertEqual(task.description, "这是一个测试任务")
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertEqual(task.priority, Priority.P1)

    def test_create_task_with_project(self):
        """创建带项目ID的任务"""
        task = self.manager.create_task(
            title="项目任务",
            project_id="proj-123",
            priority=Priority.P0,
        )
        self.assertEqual(task.project_id, "proj-123")
        self.assertEqual(task.priority, Priority.P0)

    def test_create_task_with_goal(self):
        """创建带目标ID的任务"""
        task = self.manager.create_task(
            title="目标任务",
            goal_id="goal-456",
        )
        self.assertEqual(task.goal_id, "goal-456")

    def test_create_task_assigned_agent(self):
        """创建分配了Agent的任务"""
        task = self.manager.create_task(
            title="分配任务",
            assigned_agent="agent-alpha",
        )
        self.assertEqual(task.assigned_agent, "agent-alpha")

    def test_create_task_with_estimated_hours(self):
        """创建带预估工时的任务"""
        task = self.manager.create_task(
            title="预估工时任务",
            estimated_hours=8.0,
        )
        self.assertEqual(task.estimated_hours, 8.0)

    def test_create_multiple_tasks_unique_ids(self):
        """创建多个任务ID唯一"""
        task1 = self.manager.create_task(title="任务1")
        task2 = self.manager.create_task(title="任务2")
        task3 = self.manager.create_task(title="任务3")
        self.assertNotEqual(task1.id, task2.id)
        self.assertNotEqual(task2.id, task3.id)


class TestTaskManagerGet(unittest.TestCase):
    """测试 get_task 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="待获取任务")

    def test_get_task_exists(self):
        """获取存在的任务"""
        retrieved = self.manager.get_task(self.task.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, self.task.id)
        self.assertEqual(retrieved.title, "待获取任务")

    def test_get_task_not_exists(self):
        """获取不存在的任务返回 None"""
        retrieved = self.manager.get_task("non-existent-id")
        self.assertIsNone(retrieved)


class TestTaskManagerUpdate(unittest.TestCase):
    """测试 update_task 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="原标题", description="原描述")

    def test_update_title(self):
        """更新任务标题"""
        updated = self.manager.update_task(self.task.id, title="新标题")
        self.assertEqual(updated.title, "新标题")
        self.assertEqual(updated.description, "原描述")  # 描述不变

    def test_update_description(self):
        """更新任务描述"""
        updated = self.manager.update_task(self.task.id, description="新描述")
        self.assertEqual(updated.title, "原标题")  # 标题不变
        self.assertEqual(updated.description, "新描述")

    def test_update_both(self):
        """同时更新标题和描述"""
        updated = self.manager.update_task(
            self.task.id,
            title="新标题",
            description="新描述"
        )
        self.assertEqual(updated.title, "新标题")
        self.assertEqual(updated.description, "新描述")

    def test_update_nonexistent_raises(self):
        """更新不存在的任务抛出异常"""
        with self.assertRaises(ValueError) as ctx:
            self.manager.update_task("non-existent-id", title="新标题")
        self.assertIn("not found", str(ctx.exception))


class TestTaskManagerDelete(unittest.TestCase):
    """测试 delete_task 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="待删除任务")

    def test_delete_task_exists(self):
        """删除存在的任务"""
        result = self.manager.delete_task(self.task.id)
        self.assertTrue(result)
        # 验证已被删除
        self.assertIsNone(self.manager.get_task(self.task.id))

    def test_delete_task_not_exists(self):
        """删除不存在的任务返回 False"""
        result = self.manager.delete_task("non-existent-id")
        self.assertFalse(result)


class TestTaskManagerList(unittest.TestCase):
    """测试 list_tasks 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task1 = self.manager.create_task(
            title="任务1",
            project_id="proj-A",
            assigned_agent="agent-1",
            priority=Priority.P1,
        )
        self.task2 = self.manager.create_task(
            title="任务2",
            project_id="proj-A",
            assigned_agent="agent-2",
            priority=Priority.P0,
        )
        self.task3 = self.manager.create_task(
            title="任务3",
            project_id="proj-B",
            assigned_agent="agent-1",
            priority=Priority.P2,
        )
        # 设置状态
        self.manager.update_status(self.task1.id, TaskStatus.TODO)
        self.manager.update_status(self.task2.id, TaskStatus.IN_PROGRESS)
        self.manager.update_status(self.task3.id, TaskStatus.DONE)

    def test_list_all(self):
        """列出所有任务"""
        tasks = self.manager.list_tasks()
        self.assertEqual(len(tasks), 3)

    def test_list_filter_by_status(self):
        """按状态过滤"""
        tasks = self.manager.list_tasks(status=TaskStatus.TODO)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, self.task1.id)

        tasks = self.manager.list_tasks(status=TaskStatus.IN_PROGRESS)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, self.task2.id)

        tasks = self.manager.list_tasks(status=TaskStatus.DONE)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, self.task3.id)

    def test_list_filter_by_project(self):
        """按项目过滤"""
        tasks = self.manager.list_tasks(project_id="proj-A")
        self.assertEqual(len(tasks), 2)

        tasks = self.manager.list_tasks(project_id="proj-B")
        self.assertEqual(len(tasks), 1)

    def test_list_filter_by_agent(self):
        """按Agent过滤"""
        tasks = self.manager.list_tasks(assigned_agent="agent-1")
        self.assertEqual(len(tasks), 2)

        tasks = self.manager.list_tasks(assigned_agent="agent-2")
        self.assertEqual(len(tasks), 1)

    def test_list_combined_filters(self):
        """组合过滤"""
        tasks = self.manager.list_tasks(
            status=TaskStatus.TODO,
            project_id="proj-A",
            assigned_agent="agent-1"
        )
        self.assertEqual(len(tasks), 1)


class TestTaskManagerStatusTransition(unittest.TestCase):
    """测试任务状态流转"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="状态测试任务")

    def test_status_todo_to_in_progress(self):
        """TODO -> IN_PROGRESS"""
        updated = self.manager.update_status(self.task.id, TaskStatus.IN_PROGRESS)
        self.assertEqual(updated.status, TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(updated.started_at)

    def test_status_in_progress_to_done(self):
        """IN_PROGRESS -> DONE"""
        self.manager.update_status(self.task.id, TaskStatus.IN_PROGRESS)
        updated = self.manager.update_status(self.task.id, TaskStatus.DONE)
        self.assertEqual(updated.status, TaskStatus.DONE)
        self.assertIsNotNone(updated.completed_at)

    def test_status_todo_to_done(self):
        """TODO -> DONE (直接完成)"""
        updated = self.manager.update_status(self.task.id, TaskStatus.DONE)
        self.assertEqual(updated.status, TaskStatus.DONE)
        self.assertIsNotNone(updated.completed_at)

    def test_status_to_blocked(self):
        """设置为 BLOCKED"""
        updated = self.manager.update_status(self.task.id, TaskStatus.BLOCKED)
        self.assertEqual(updated.status, TaskStatus.BLOCKED)

    def test_status_to_cancelled(self):
        """设置为 CANCELLED"""
        updated = self.manager.update_status(self.task.id, TaskStatus.CANCELLED)
        self.assertEqual(updated.status, TaskStatus.CANCELLED)


class TestTaskManagerComplete(unittest.TestCase):
    """测试 complete_task 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="待完成任务")

    def test_complete_basic(self):
        """基本完成"""
        completed = self.manager.complete_task(self.task.id, result="完成结果")
        self.assertEqual(completed.status, TaskStatus.DONE)
        self.assertEqual(completed.result, "完成结果")
        self.assertIsNotNone(completed.completed_at)

    def test_complete_with_actual_hours(self):
        """完成并记录实际工时"""
        completed = self.manager.complete_task(
            self.task.id,
            result="完成",
            actual_hours=5.5
        )
        self.assertEqual(completed.actual_hours, 5.5)

    def test_complete_nonexistent_raises(self):
        """完成不存在的任务抛出异常"""
        with self.assertRaises(ValueError):
            self.manager.complete_task("non-existent-id")


class TestTaskManagerFail(unittest.TestCase):
    """测试 fail_task 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="待失败任务")

    def test_fail_basic(self):
        """标记失败"""
        failed = self.manager.fail_task(self.task.id, error="未知错误")
        self.assertEqual(failed.status, TaskStatus.TODO)  # 失败后回到TODO
        self.assertIn("FAILED", failed.result)
        self.assertIn("未知错误", failed.result)


class TestTaskManagerAssign(unittest.TestCase):
    """测试 assign 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.task = self.manager.create_task(title="待分配任务")

    def test_assign_agent(self):
        """分配Agent"""
        updated = self.manager.assign(self.task.id, "agent-new")
        self.assertEqual(updated.assigned_agent, "agent-new")

    def test_assign_nonexistent_raises(self):
        """分配不存在的任务抛出异常"""
        with self.assertRaises(ValueError):
            self.manager.assign("non-existent-id", "agent-new")


class TestTaskManagerDependencies(unittest.TestCase):
    """测试任务依赖"""

    def setUp(self):
        self.manager = TaskManager()
        self.task1 = self.manager.create_task(title="前置任务")
        self.task2 = self.manager.create_task(title="依赖任务")

    def test_add_dependency(self):
        """添加依赖"""
        updated = self.manager.add_dependency(self.task2.id, self.task1.id)
        self.assertIn(self.task1.id, updated.dependencies)

    def test_remove_dependency(self):
        """移除依赖"""
        self.manager.add_dependency(self.task2.id, self.task1.id)
        updated = self.manager.remove_dependency(self.task2.id, self.task1.id)
        self.assertNotIn(self.task1.id, updated.dependencies)

    def test_can_start_no_dependencies(self):
        """无依赖任务可以开始"""
        self.assertTrue(self.manager.can_start(self.task1.id))

    def test_can_start_with_undone_dependency(self):
        """有未完成依赖的任务不能开始"""
        self.manager.add_dependency(self.task2.id, self.task1.id)
        self.assertFalse(self.manager.can_start(self.task2.id))

    def test_can_start_with_done_dependency(self):
        """依赖都完成时任务可以开始"""
        self.manager.add_dependency(self.task2.id, self.task1.id)
        self.manager.complete_task(self.task1.id)
        self.assertTrue(self.manager.can_start(self.task2.id))

    def test_get_ready_tasks(self):
        """获取可执行任务"""
        ready = self.manager.get_ready_tasks()
        # task1 无依赖，应该在 ready 列表
        self.assertGreaterEqual(len(ready), 1)

    def test_get_blocked_tasks(self):
        """获取被阻塞任务"""
        self.manager.add_dependency(self.task2.id, self.task1.id)
        blocked = self.manager.get_blocked_tasks()
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0].id, self.task2.id)


class TestTaskManagerTaskStats(unittest.TestCase):
    """测试任务统计"""

    def setUp(self):
        self.manager = TaskManager()
        self.t1 = self.manager.create_task(title="任务1", priority=Priority.P0)
        self.t2 = self.manager.create_task(title="任务2", priority=Priority.P1)
        self.t3 = self.manager.create_task(title="任务3", priority=Priority.P1)
        self.t4 = self.manager.create_task(title="任务4", priority=Priority.P2)
        self.t5 = self.manager.create_task(title="任务5", priority=Priority.P0)
        # 设置状态
        self.manager.update_status(self.t1.id, TaskStatus.TODO)
        self.manager.update_status(self.t2.id, TaskStatus.IN_PROGRESS)
        self.manager.update_status(self.t3.id, TaskStatus.DONE)
        self.manager.update_status(self.t4.id, TaskStatus.DONE)
        self.manager.update_status(self.t5.id, TaskStatus.BLOCKED)

    def test_stats_total(self):
        """统计总数"""
        stats = self.manager.get_task_stats()
        self.assertEqual(stats["total"], 5)

    def test_stats_by_status(self):
        """按状态统计"""
        stats = self.manager.get_task_stats()
        self.assertEqual(stats["todo"], 1)
        self.assertEqual(stats["in_progress"], 1)
        self.assertEqual(stats["done"], 2)
        self.assertEqual(stats["blocked"], 1)

    def test_stats_by_priority(self):
        """按优先级统计"""
        stats = self.manager.get_task_stats()
        # Priority keys are integers (0, 1, 2) not strings
        self.assertEqual(stats["by_priority"][0], 2)  # P0
        self.assertEqual(stats["by_priority"][1], 2)  # P1
        self.assertEqual(stats["by_priority"][2], 1)  # P2

    def test_stats_completion_rate(self):
        """完成率"""
        stats = self.manager.get_task_stats()
        self.assertAlmostEqual(stats["completion_rate"], 0.4)  # 2/5


class TestTaskManagerGetAgentTasks(unittest.TestCase):
    """测试 get_agent_tasks 功能"""

    def setUp(self):
        self.manager = TaskManager()
        self.agent = "agent-test"
        self.t1 = self.manager.create_task(
            title="Agent任务1",
            assigned_agent=self.agent,
        )
        self.t2 = self.manager.create_task(
            title="Agent任务2",
            assigned_agent=self.agent,
        )
        self.t3 = self.manager.create_task(
            title="其他Agent任务",
            assigned_agent="other-agent",
        )
        self.manager.update_status(self.t1.id, TaskStatus.TODO)
        self.manager.update_status(self.t2.id, TaskStatus.DONE)

    def test_get_agent_tasks_all(self):
        """获取指定Agent的所有任务"""
        tasks = self.manager.get_agent_tasks(self.agent)
        self.assertEqual(len(tasks), 2)

    def test_get_agent_tasks_filtered_by_status(self):
        """获取指定Agent的特定状态任务"""
        tasks = self.manager.get_agent_tasks(self.agent, status=TaskStatus.TODO)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, self.t1.id)

        tasks = self.manager.get_agent_tasks(self.agent, status=TaskStatus.DONE)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, self.t2.id)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Reins Backend 单元测试")
    print("=" * 60)
    unittest.main(verbosity=2)
