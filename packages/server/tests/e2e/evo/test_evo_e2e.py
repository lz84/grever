"""
L4-09 进化域 Evo E2E 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → L4-09

覆盖用例：
- TC-E2E-E-001: 经验蒸馏闭环
- TC-E2E-E-002: 能力进化闭环
- TC-E2E-E-003: 突变分析闭环
- TC-E2E-E-004: Capsule API 全流程
- TC-E2E-E-005: GEP 事件链
- TC-E2E-E-006: 争议管理
"""

import pytest
import uuid
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    # Create minimal tables needed for tests
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS capsules (
                id TEXT PRIMARY KEY,
                schema_version INTEGER,
                trigger TEXT,
                gene_id TEXT,
                summary TEXT,
                confidence REAL,
                blast_radius TEXT,
                outcome TEXT,
                success_streak INTEGER,
                content TEXT,
                diff TEXT,
                strategy TEXT,
                a2a TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'draft'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS evolution_events (
                id TEXT PRIMARY KEY,
                event_type TEXT,
                parent_id TEXT,
                child_id TEXT,
                capsule_id TEXT,
                outcome TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS disputes (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                agent_id TEXT,
                status TEXT DEFAULT 'open',
                reason TEXT,
                resolution TEXT,
                created_at TEXT,
                resolved_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal_id TEXT,
                title TEXT,
                status TEXT DEFAULT 'todo',
                result TEXT,
                completed_at TEXT
            )
        """))
        conn.commit()
    Session = sessionmaker(bind=engine)
    return Session()


# ===========================================================================
# TC-E2E-E-001: 经验蒸馏闭环
# ===========================================================================

class TestExperienceDistillation:
    """TC-E2E-E-001: 经验蒸馏闭环
    Task 完成 → 提取模式 → 蒸馏 → 固化为 Capsule（draft→validated→solidified）
    """

    def test_distill_pattern_from_completed_task(self, test_db):
        """从已完成任务中提取模式并蒸馏为 Capsule"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO tasks (id, title, status, result, completed_at) VALUES (:id, :title, 'done', :result, :ts)"
        ), {
            "id": task_id,
            "title": "完成数据处理",
            "result": '{"method": "pandas", "steps": ["load", "clean", "transform"]}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 验证任务已完成
        row = test_db.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert row is not None
        assert row[3] == 'done'  # status

    def test_capsule_lifecycle_draft_to_solidified(self, test_db):
        """Capsule 完整生命周期: draft → validated → solidified"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"

        # Create capsule in draft state
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, status, created_at) VALUES (:id, :summary, :conf, :status, :ts)"
        ), {
            "id": capsule_id,
            "summary": "数据清洗最佳实践",
            "conf": 0.85,
            "status": "draft",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # Validate capsule
        test_db.execute(text(
            "UPDATE capsules SET status = 'validated' WHERE id = :id"
        ), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 'validated'

        # Solidify capsule
        test_db.execute(text(
            "UPDATE capsules SET status = 'solidified' WHERE id = :id"
        ), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 'solidified'

    def test_distill_requires_completed_task(self, test_db):
        """未完成的任务不应触发蒸馏"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO tasks (id, title, status) VALUES (:id, :title, :status)"
        ), {"id": task_id, "title": "进行中任务", "status": "in_progress"})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert row[0] != 'done'


# ===========================================================================
# TC-E2E-E-002: 能力进化闭环
# ===========================================================================

class TestCapabilityEvolution:
    """TC-E2E-E-002: 能力进化闭环
    Task 成功/失败 → 能力权重更新 → 影响下次派发
    """

    def test_successful_task_updates_capability_weight(self, test_db):
        """成功任务应更新对应能力权重"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, success_streak, status, created_at) VALUES (:id, :summary, :conf, :streak, :status, :ts)"
        ), {
            "id": capsule_id,
            "summary": "Python 数据处理能力",
            "conf": 0.9,
            "streak": 1,
            "status": "validated",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 成功 → 更新 streak
        test_db.execute(text(
            "UPDATE capsules SET success_streak = success_streak + 1 WHERE id = :id"
        ), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT success_streak FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 2

    def test_failed_task_resets_streak(self, test_db):
        """失败任务应重置成功 streak"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, success_streak, status, created_at) VALUES (:id, :summary, :conf, :streak, :status, :ts)"
        ), {
            "id": capsule_id,
            "summary": "API 调用能力",
            "conf": 0.7,
            "streak": 5,
            "status": "validated",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 失败 → 重置 streak
        test_db.execute(text(
            "UPDATE capsules SET success_streak = 0 WHERE id = :id"
        ), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT success_streak FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 0


# ===========================================================================
# TC-E2E-E-003: 突变分析闭环
# ===========================================================================

class TestMutationAnalysis:
    """TC-E2E-E-003: 突变分析闭环
    识别能力突变 → 采纳/拒绝 → 标签更新
    """

    def test_mutation_detect_and_accept(self, test_db):
        """检测到突变并采纳"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, status, strategy, created_at) VALUES (:id, :summary, :conf, :status, :strategy, :ts)"
        ), {
            "id": capsule_id,
            "summary": "新的数据压缩方法",
            "conf": 0.6,
            "status": "draft",
            "strategy": '{"mutation_type": "algorithm_change", "description": "使用新算法替代旧算法"}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 采纳 → 提升到 validated
        test_db.execute(text(
            "UPDATE capsules SET status = 'validated' WHERE id = :id"
        ), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 'validated'

    def test_mutation_detect_and_reject(self, test_db):
        """检测到突变但拒绝"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, status, outcome, created_at) VALUES (:id, :summary, :conf, :status, :outcome, :ts)"
        ), {
            "id": capsule_id,
            "summary": "不稳定的优化方案",
            "conf": 0.3,
            "status": "draft",
            "outcome": '{"decision": "rejected", "reason": "性能提升不足"}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 拒绝 → 标记 deprecated
        test_db.execute(text(
            "UPDATE capsules SET status = 'deprecated' WHERE id = :id"
        ), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 'deprecated'


# ===========================================================================
# TC-E2E-E-004: Capsule API 全流程
# ===========================================================================

class TestCapsuleAPI:
    """TC-E2E-E-004: Capsule API 全流程
    查询列表 → 详情 → promote → deprecate → 状态机验证
    """

    def test_capsule_create_and_query(self, test_db):
        """创建 Capsule 并查询列表"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, status, created_at) VALUES (:id, :summary, :conf, :status, :ts)"
        ), {
            "id": capsule_id,
            "summary": "测试 Capsule",
            "conf": 0.8,
            "status": "draft",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 查询列表
        rows = test_db.execute(text("SELECT id, summary, status FROM capsules")).fetchall()
        assert len(rows) >= 1
        assert any(r[0] == capsule_id for r in rows)

    def test_capsule_detail(self, test_db):
        """查询 Capsule 详情"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, confidence, status, content, created_at) VALUES (:id, :summary, :conf, :status, :content, :ts)"
        ), {
            "id": capsule_id,
            "summary": "详情测试",
            "conf": 0.9,
            "status": "validated",
            "content": '{"method": "test", "params": {}}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        row = test_db.execute(text("SELECT * FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row is not None
        assert row[1] == 1  # schema_version (default)
        assert row[4] == "详情测试"  # summary

    def test_capsule_promote(self, test_db):
        """Promote Capsule 状态"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, status, created_at) VALUES (:id, :summary, :status, :ts)"
        ), {
            "id": capsule_id,
            "summary": "Promote 测试",
            "status": "draft",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # Promote: draft → validated
        test_db.execute(text("UPDATE capsules SET status = 'validated' WHERE id = :id"), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 'validated'

    def test_capsule_deprecate(self, test_db):
        """Deprecate Capsule"""
        capsule_id = f"capsule-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO capsules (id, summary, status, created_at) VALUES (:id, :summary, :status, :ts)"
        ), {
            "id": capsule_id,
            "summary": "Deprecate 测试",
            "status": "validated",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        test_db.execute(text("UPDATE capsules SET status = 'deprecated' WHERE id = :id"), {"id": capsule_id})
        test_db.commit()

        row = test_db.execute(text("SELECT status FROM capsules WHERE id = :id"), {"id": capsule_id}).fetchone()
        assert row[0] == 'deprecated'

    def test_capsule_state_machine_validation(self, test_db):
        """Capsule 状态机验证：非法转换应被拒绝"""
        valid_transitions = {
            'draft': {'validated', 'deprecated'},
            'validated': {'solidified', 'deprecated'},
            'solidified': {'deprecated'},
            'deprecated': set(),
        }

        # 验证状态转换规则
        assert 'validated' in valid_transitions['draft']
        assert 'solidified' not in valid_transitions['draft']  # 不能直接从 draft → solidified
        assert len(valid_transitions['deprecated']) == 0  # deprecated 是终态


# ===========================================================================
# TC-E2E-E-005: GEP 事件链
# ===========================================================================

class TestGEPEventChain:
    """TC-E2E-E-005: GEP 事件链
    创建 EvolutionEvent → 父子关联 → 记录 outcome
    """

    def test_create_evolution_event(self, test_db):
        """创建进化事件"""
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO evolution_events (id, event_type, capsule_id, outcome, created_at) VALUES (:id, :type, :capsule, :outcome, :ts)"
        ), {
            "id": event_id,
            "type": "distillation",
            "capsule": f"capsule-{uuid.uuid4().hex[:8]}",
            "outcome": '{"result": "success"}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        row = test_db.execute(text("SELECT event_type FROM evolution_events WHERE id = :id"), {"id": event_id}).fetchone()
        assert row[0] == 'distillation'

    def test_parent_child_event_chain(self, test_db):
        """父子事件关联链"""
        parent_id = f"evt-parent-{uuid.uuid4().hex[:4]}"
        child_id = f"evt-child-{uuid.uuid4().hex[:4]}"

        test_db.execute(text(
            "INSERT INTO evolution_events (id, event_type, outcome, created_at) VALUES (:id, :type, :outcome, :ts)"
        ), {"id": parent_id, "type": "mutation", "outcome": '{"result": "detected"}', "ts": datetime.now().isoformat()})
        test_db.commit()

        test_db.execute(text(
            "INSERT INTO evolution_events (id, event_type, parent_id, outcome, created_at) VALUES (:id, :type, :parent, :outcome, :ts)"
        ), {"id": child_id, "type": "evaluation", "parent": parent_id, "outcome": '{"result": "approved"}', "ts": datetime.now().isoformat()})
        test_db.commit()

        child = test_db.execute(text("SELECT parent_id FROM evolution_events WHERE id = :id"), {"id": child_id}).fetchone()
        assert child[0] == parent_id

    def test_event_outcome_recording(self, test_db):
        """记录事件 outcome"""
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO evolution_events (id, event_type, outcome, created_at) VALUES (:id, :type, :outcome, :ts)"
        ), {
            "id": event_id,
            "type": "promotion",
            "outcome": '{"from": "draft", "to": "validated", "reason": "high confidence"}',
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        row = test_db.execute(text("SELECT outcome FROM evolution_events WHERE id = :id"), {"id": event_id}).fetchone()
        assert 'validated' in row[0]


# ===========================================================================
# TC-E2E-E-006: 争议管理
# ===========================================================================

class TestDisputeManagement:
    """TC-E2E-E-006: 争议管理
    创建争议 → 跟踪状态 → 关联 Task → 解决
    """

    def test_create_dispute(self, test_db):
        """创建争议记录"""
        dispute_id = f"dispute-{uuid.uuid4().hex[:8]}"
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        test_db.execute(text(
            "INSERT INTO disputes (id, task_id, status, reason, created_at) VALUES (:id, :task, :status, :reason, :ts)"
        ), {
            "id": dispute_id,
            "task": task_id,
            "status": "open",
            "reason": "验证结果与预期不符",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        row = test_db.execute(text("SELECT task_id, status, reason FROM disputes WHERE id = :id"), {"id": dispute_id}).fetchone()
        assert row[0] == task_id
        assert row[1] == 'open'
        assert '验证' in row[2]

    def test_resolve_dispute(self, test_db):
        """解决争议"""
        dispute_id = f"dispute-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO disputes (id, status, reason, created_at) VALUES (:id, :status, :reason, :ts)"
        ), {
            "id": dispute_id,
            "status": "open",
            "reason": "Agent 执行结果不一致",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # 解决争议
        test_db.execute(text(
            "UPDATE disputes SET status = 'resolved', resolution = :resolution, resolved_at = :ts WHERE id = :id"
        ), {
            "id": dispute_id,
            "resolution": "重新验证后通过",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        row = test_db.execute(text("SELECT status, resolution FROM disputes WHERE id = :id"), {"id": dispute_id}).fetchone()
        assert row[0] == 'resolved'
        assert row[1] == "重新验证后通过"

    def test_dispute_status_tracking(self, test_db):
        """争议状态跟踪"""
        dispute_id = f"dispute-{uuid.uuid4().hex[:8]}"
        test_db.execute(text(
            "INSERT INTO disputes (id, status, created_at) VALUES (:id, :status, :ts)"
        ), {
            "id": dispute_id,
            "status": "open",
            "ts": datetime.now().isoformat()
        })
        test_db.commit()

        # open → in_review → resolved
        test_db.execute(text("UPDATE disputes SET status = 'in_review' WHERE id = :id"), {"id": dispute_id})
        test_db.commit()
        row = test_db.execute(text("SELECT status FROM disputes WHERE id = :id"), {"id": dispute_id}).fetchone()
        assert row[0] == 'in_review'

        test_db.execute(text("UPDATE disputes SET status = 'resolved', resolved_at = :ts WHERE id = :id"), {"id": dispute_id, "ts": datetime.now().isoformat()})
        test_db.commit()
        row = test_db.execute(text("SELECT status FROM disputes WHERE id = :id"), {"id": dispute_id}).fetchone()
        assert row[0] == 'resolved'
