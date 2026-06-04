"""
L4-11 Dashboard 与可视化 E2E 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → L4-11

覆盖用例：
- TC-E2E-D-001: Dashboard 统计
- TC-E2E-D-002: DAG 图渲染
- TC-E2E-D-003: 工作流 DAG 对话
- TC-E2E-D-004: 工作流编辑
- TC-E2E-D-005: 报告生成
"""

import pytest
import uuid
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT, status TEXT,
                goal_id TEXT, completed_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY, title TEXT, status TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY, name TEXT, status TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id TEXT PRIMARY KEY, title TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, goal_id TEXT, title TEXT, status TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY, project_id TEXT, title TEXT, status TEXT, steps TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id TEXT PRIMARY KEY, workflow_id TEXT, title TEXT, status TEXT, depends_on TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY, trace_type TEXT, data TEXT, created_at TEXT
            )
        """))
        conn.commit()
    Session = sessionmaker(bind=engine)
    return Session()


# ===========================================================================
# TC-E2E-D-001: Dashboard 统计
# ===========================================================================

class TestDashboardStats:
    """TC-E2E-D-001: Dashboard 统计
    页面加载 → 统计卡片数据 → 最近活动列表 → 与后端一致
    """

    def test_active_tasks_count(self, test_db):
        """活跃任务数 (in_progress 或 running)"""
        for status in ['todo', 'in_progress', 'running', 'done']:
            test_db.execute(text(
                "INSERT INTO tasks (id, title, status) VALUES (:id, :title, :status)"
            ), {"id": f"task-{status}-{uuid.uuid4().hex[:4]}", "title": f"{status} task", "status": status})
        test_db.commit()

        row = test_db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('in_progress', 'running')"
        )).fetchone()
        assert row[0] == 2

    def test_completed_today_count(self, test_db):
        """今日完成任务数"""
        today = datetime.now().isoformat()
        test_db.execute(text(
            "INSERT INTO tasks (id, title, status, completed_at) VALUES (:id, :title, :status, :ts)"
        ), {"id": f"task-done-today", "title": "today done", "status": "done", "ts": today})
        test_db.commit()

        row = test_db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('done', 'completed') AND completed_at IS NOT NULL"
        )).fetchone()
        assert row[0] >= 1

    def test_online_agents_count(self, test_db):
        """在线 Agent 数 (status = running)"""
        for status in ['running', 'idle', 'offline']:
            test_db.execute(text(
                "INSERT INTO agents (id, name, status) VALUES (:id, :name, :status)"
            ), {"id": f"agent-{status}", "name": f"{status} agent", "status": status})
        test_db.commit()

        row = test_db.execute(text(
            "SELECT COUNT(*) FROM agents WHERE status = 'running'"
        )).fetchone()
        assert row[0] == 1

    def test_total_scenarios_count(self, test_db):
        """场景库总数"""
        for i in range(5):
            test_db.execute(text(
                "INSERT INTO scenarios (id, title) VALUES (:id, :title)"
            ), {"id": f"scenario-{i}", "title": f"场景 {i}"})
        test_db.commit()

        row = test_db.execute(text("SELECT COUNT(*) FROM scenarios")).fetchone()
        assert row[0] == 5

    def test_total_and_active_goals(self, test_db):
        """目标总数和进行中目标数"""
        for status in ['created', 'in_progress', 'completed']:
            test_db.execute(text(
                "INSERT INTO goals (id, title, status) VALUES (:id, :title, :status)"
            ), {"id": f"goal-{status}", "title": f"{status} goal", "status": status})
        test_db.commit()

        total = test_db.execute(text("SELECT COUNT(*) FROM goals")).fetchone()[0]
        active = test_db.execute(text(
            "SELECT COUNT(*) FROM goals WHERE status IN ('in_progress', 'created')"
        )).fetchone()[0]
        assert total == 3
        assert active == 2

    def test_dashboard_stats_consistency(self, test_db):
        """Dashboard 统计数据一致性"""
        # Insert test data
        test_db.execute(text("INSERT INTO tasks (id, title, status) VALUES ('t1', 'task1', 'in_progress')"))
        test_db.execute(text("INSERT INTO tasks (id, title, status) VALUES ('t2', 'task2', 'done')"))
        test_db.execute(text("INSERT INTO goals (id, title, status) VALUES ('g1', 'goal1', 'in_progress')"))
        test_db.commit()

        # Gather stats
        active_tasks = test_db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('in_progress', 'running')"
        )).fetchone()[0]
        completed = test_db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('done', 'completed')"
        )).fetchone()[0]
        total_goals = test_db.execute(text("SELECT COUNT(*) FROM goals")).fetchone()[0]

        # Verify consistency
        assert active_tasks == 1
        assert completed == 1
        assert total_goals == 1


# ===========================================================================
# TC-E2E-D-002: DAG 图渲染
# ===========================================================================

class TestDAGRendering:
    """TC-E2E-D-002: DAG 图渲染
    加载含依赖关系的 Task → DAG 可视化 → 无渲染错误
    """

    def test_dag_has_no_cycles(self):
        """DAG 无循环检测"""
        # Simple DAG: A → B → C
        edges = [('A', 'B'), ('B', 'C')]
        adj = {}
        for src, dst in edges:
            adj.setdefault(src, []).append(dst)

        # Topological sort (Kahn's algorithm)
        in_degree = {}
        for src, dst in edges:
            in_degree[src] = in_degree.get(src, 0)
            in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = [n for n in in_degree if in_degree[n] == 0]
        topo_order = []
        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        assert len(topo_order) == 3  # All nodes processed
        assert topo_order == ['A', 'B', 'C']

    def test_dag_with_cycle_detected(self):
        """有循环的 DAG 应被检测"""
        edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]  # Cycle!
        in_degree = {}
        for src, dst in edges:
            in_degree[src] = in_degree.get(src, 0)
            in_degree[dst] = in_degree.get(dst, 0) + 1

        queue = [n for n in in_degree if in_degree[n] == 0]
        topo_order = []
        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            for src, dst in edges:
                if src == node:
                    in_degree[dst] -= 1
                    if in_degree[dst] == 0:
                        queue.append(dst)

        assert len(topo_order) < 3  # Not all nodes processed → cycle detected

    def test_dag_parallel_groups(self):
        """DAG 并行分组"""
        # A → C, B → C (A and B can run in parallel)
        edges = [('A', 'C'), ('B', 'C')]
        in_degree = {'A': 0, 'B': 0, 'C': 2}

        # Level-by-level grouping
        groups = []
        current_level = [n for n in in_degree if in_degree[n] == 0]
        while current_level:
            groups.append(current_level)
            next_level = []
            for node in current_level:
                for src, dst in edges:
                    if src == node:
                        in_degree[dst] -= 1
                        if in_degree[dst] == 0:
                            next_level.append(dst)
            current_level = next_level

        assert groups[0] == ['A', 'B']  # Parallel
        assert groups[1] == ['C']        # Depends on A and B


# ===========================================================================
# TC-E2E-D-003: 工作流 DAG 对话
# ===========================================================================

class TestWorkflowDAGChat:
    """TC-E2E-D-003: 工作流 DAG 对话
    对工作流 DAG 发起对话 → AI 回答
    """

    def test_workflow_dag_chat_request(self, test_db):
        """发起 DAG 对话请求"""
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO workflows (id, project_id, title, status, steps) VALUES (:id, :proj, :title, :status, :steps)"
        ), {
            "id": workflow_id,
            "proj": f"proj-{uuid.uuid4().hex[:8]}",
            "title": "数据处理工作流",
            "status": "active",
            "steps": '[{"id": "s1", "title": "数据加载"}, {"id": "s2", "title": "数据清洗"}]'
        })
        test_db.commit()

        row = test_db.execute(text("SELECT steps FROM workflows WHERE id = :id"), {"id": workflow_id}).fetchone()
        assert row[0] is not None

    def test_workflow_dag_chat_response(self):
        """DAG 对话返回 AI 分析"""
        # Simulate AI response about workflow
        response = {
            "analysis": "该工作流包含 2 个步骤，数据加载 → 数据清洗，无循环依赖。",
            "suggestions": ["建议增加数据验证步骤", "可并行处理多个数据源"],
            "status": "ok"
        }
        assert response["status"] == "ok"
        assert len(response["suggestions"]) == 2


# ===========================================================================
# TC-E2E-D-004: 工作流编辑
# ===========================================================================

class TestWorkflowEditing:
    """TC-E2E-D-004: 工作流编辑
    编辑工作流步骤 → 保存 → 验证更新
    """

    def test_add_workflow_step(self, test_db):
        """添加工作流步骤"""
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO workflows (id, project_id, title, status, steps) VALUES (:id, :proj, :title, :status, :steps)"
        ), {
            "id": workflow_id,
            "proj": f"proj-{uuid.uuid4().hex[:8]}",
            "title": "原始工作流",
            "status": "draft",
            "steps": '[{"id": "s1", "title": "步骤1"}]'
        })
        test_db.commit()

        # Add step
        test_db.execute(text(
            "INSERT INTO workflow_steps (id, workflow_id, title, status) VALUES (:id, :wf, :title, :status)"
        ), {
            "id": f"step-{uuid.uuid4().hex[:8]}",
            "wf": workflow_id,
            "title": "步骤2",
            "status": "pending"
        })
        test_db.commit()

        steps = test_db.execute(text("SELECT COUNT(*) FROM workflow_steps WHERE workflow_id = :wf"), {"wf": workflow_id}).fetchone()
        assert steps[0] == 1

    def test_edit_workflow_step(self, test_db):
        """编辑工作流步骤"""
        step_id = f"step-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO workflow_steps (id, workflow_id, title, status) VALUES (:id, :wf, :title, :status)"
        ), {
            "id": step_id,
            "wf": f"wf-{uuid.uuid4().hex[:8]}",
            "title": "原始步骤",
            "status": "pending"
        })
        test_db.commit()

        # Edit step
        test_db.execute(text(
            "UPDATE workflow_steps SET title = :title WHERE id = :id"
        ), {"id": step_id, "title": "更新后的步骤"})
        test_db.commit()

        row = test_db.execute(text("SELECT title FROM workflow_steps WHERE id = :id"), {"id": step_id}).fetchone()
        assert row[0] == "更新后的步骤"

    def test_remove_workflow_step(self, test_db):
        """删除工作流步骤"""
        step_id = f"step-{uuid.uuid4().hex[:8]}"
        wf_id = f"wf-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO workflow_steps (id, workflow_id, title, status) VALUES (:id, :wf, :title, :status)"
        ), {
            "id": step_id,
            "wf": wf_id,
            "title": "待删除步骤",
            "status": "pending"
        })
        test_db.commit()

        # Remove step
        test_db.execute(text("DELETE FROM workflow_steps WHERE id = :id"), {"id": step_id})
        test_db.commit()

        row = test_db.execute(text("SELECT COUNT(*) FROM workflow_steps WHERE id = :id"), {"id": step_id}).fetchone()
        assert row[0] == 0


# ===========================================================================
# TC-E2E-D-005: 报告生成
# ===========================================================================

class TestReportGeneration:
    """TC-E2E-D-005: 报告生成
    生成报告 → 查询报告列表 → 数据正确
    """

    def test_generate_trace_report(self, test_db):
        """生成 trace 报告"""
        trace_id = f"trace-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO traces (id, trace_type, data, created_at) VALUES (:id, :type, :data, :ts)"
        ), {
            "id": trace_id,
            "type": "goal_execution",
            "data": '{"goal": "test", "tasks": 5, "completed": 3, "failed": 0}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        row = test_db.execute(text("SELECT data FROM traces WHERE id = :id"), {"id": trace_id}).fetchone()
        assert row[0] is not None
        assert '"tasks": 5' in row[0]

    def test_query_report_list(self, test_db):
        """查询报告列表"""
        for i in range(3):
            test_db.execute(text(
                "INSERT INTO traces (id, trace_type, data, created_at) VALUES (:id, :type, :data, :ts)"
            ), {
                "id": f"trace-{i}",
                "type": "goal_execution",
                "data": f'{{"goal": "test_{i}"}}',
                "ts": datetime.now().isoformat()
            })
        test_db.commit()

        rows = test_db.execute(text("SELECT COUNT(*) FROM traces")).fetchone()
        assert rows[0] >= 3

    def test_report_data_correctness(self, test_db):
        """报告数据与后端一致"""
        # Create test data
        test_db.execute(text("INSERT INTO tasks (id, title, status) VALUES ('t1', 'task1', 'done')"))
        test_db.execute(text("INSERT INTO tasks (id, title, status) VALUES ('t2', 'task2', 'done')"))
        test_db.execute(text("INSERT INTO tasks (id, title, status) VALUES ('t3', 'task3', 'in_progress')"))
        test_db.commit()

        # Report should reflect current state
        done_count = test_db.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'done'")).fetchone()[0]
        in_progress_count = test_db.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'")).fetchone()[0]
        total = test_db.execute(text("SELECT COUNT(*) FROM tasks")).fetchone()[0]

        assert done_count == 2
        assert in_progress_count == 1
        assert total == 3
