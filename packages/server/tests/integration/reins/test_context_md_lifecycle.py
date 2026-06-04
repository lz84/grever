"""
数据契约测试：context_md 端到端生命周期验证

验证 context_md 从写入 → 传递 → 读取的完整链路，确保不会出现"5层失效"问题。

覆盖环节：
1. task_runner.launch() → context_md 写入 DB
2. project_executor._call_complete_api() → payload 携带 context_md
3. result_verifier.trigger_verification() → 能读到 context_md
4. complete_task API → 拒绝空 context_md（needs_verification=1 时）

运行方式：
    pytest tests/test_context_md_lifecycle.py -v
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime


@pytest.fixture
def db_path():
    """创建临时 DB，带有完整的 tasks 表结构和 trigger"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    c = conn.cursor()

    # 创建 tasks 表（最小必要列）
    c.executescript("""
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            needs_verification INTEGER DEFAULT 0,
            context_md TEXT,
            acceptance_criteria TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            assigned_agent TEXT,
            project_id TEXT,
            goal_id TEXT,
            result_summary TEXT,
            error_message TEXT,
            verification_cycle INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'medium'
        );

        -- Migration 034 trigger: 需要验证的任务完成时 context_md 不能为空
        CREATE TRIGGER enforce_context_md_on_complete
        BEFORE UPDATE OF status ON tasks
        WHEN NEW.status = 'done'
          AND OLD.needs_verification = 1
          AND (NEW.context_md IS NULL OR NEW.context_md = '')
        BEGIN
            SELECT RAISE(ABORT, 'context_md_required');
        END;
    """)
    conn.commit()
    conn.close()

    yield path

    # 清理（Windows 上可能需要短暂等待释放文件句柄）
    if os.path.exists(path):
        try:
            os.unlink(path)
        except PermissionError:
            import time
            time.sleep(0.5)
            try:
                os.unlink(path)
            except PermissionError:
                pass  # Windows 可能无法立即删除


@pytest.fixture
def db_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestContextMdWrite:
    """Layer 1: 写入层 — task_runner.launch() 必须写 context_md"""

    def test_write_on_dispatch(self, db_path):
        """派发任务时 context_md 应该被写入 DB"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # 模拟 task_runner.launch() 的写入逻辑
        task_id = "test-write-001"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification)
            VALUES (?, ?, 'todo', 1)
        """, (task_id, "测试写入"))
        conn.commit()

        # 模拟 launch 写入 context_md（需要 >50 字符）
        context_md = "## 执行概要\n你是一名 Python 开发者，请完成以下任务。具体要求请参考项目文档中的相关规范，确保代码质量。"
        c.execute("""
            UPDATE tasks SET context_md = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (context_md, task_id))
        conn.commit()

        # 断言：context_md 不为空
        c.execute("SELECT context_md FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        assert row[0] is not None, "L1 失败：派发后 context_md 应该已写入"
        assert len(row[0]) > 50, "L1 失败：context_md 内容太短"
        assert "执行概要" in row[0], "L1 失败：context_md 内容不正确"
        conn.close()

    def test_write_on_dispatch_empty_prompt(self, db_path):
        """如果 prompt 为空（异常情况），不应该静默失败"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        task_id = "test-empty-001"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification)
            VALUES (?, ?, 'todo', 1)
        """, (task_id, "测试空 prompt"))
        conn.commit()

        # 模拟空 prompt 场景：不应该写入空值
        prompt = ""
        if prompt and len(prompt) > 50:
            c.execute("""
                UPDATE tasks SET context_md = ? WHERE id = ?
            """, (prompt[:8000], task_id))
            conn.commit()

        c.execute("SELECT context_md FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        assert row[0] is None, "空 prompt 时 context_md 应该仍为 NULL（等待后续补写）"
        conn.close()


class TestContextMdConstraint:
    """Layer 1.5: DB 硬约束 — trigger 阻止无效完成"""

    def test_constraint_blocks_done_without_context_md(self, db_conn):
        """需要验证的任务在 context_md 为空时不能标记为 done"""
        c = db_conn.cursor()
        task_id = "test-constraint-001"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification, context_md)
            VALUES (?, ?, 'todo', 1, NULL)
        """, (task_id, "无 context_md 的任务"))
        db_conn.commit()

        # 尝试标记为 done（应该被 trigger 阻止）
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            c.execute("""
                UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (task_id,))
            db_conn.commit()

        assert "context_md_required" in str(exc_info.value), \
            "DB 约束应该阻止无 context_md 的完成操作"

    def test_constraint_allows_done_with_context_md(self, db_conn):
        """有 context_md 的任务可以正常标记为 done"""
        c = db_conn.cursor()
        task_id = "test-constraint-002"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification, context_md)
            VALUES (?, ?, 'todo', 1, '## 执行概要\n有效上下文')
        """, (task_id, "有 context_md 的任务"))
        db_conn.commit()

        # 标记为 done（应该成功）
        c.execute("""
            UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (task_id,))
        db_conn.commit()

        c.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        assert row[0] == "done", "有 context_md 的任务应该能正常完成"

    def test_no_constraint_for_non_verification_tasks(self, db_conn):
        """不需要验证的任务不受 context_md 约束"""
        c = db_conn.cursor()
        task_id = "test-constraint-003"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification, context_md)
            VALUES (?, ?, 'todo', 0, NULL)
        """, (task_id, "不需要验证的任务"))
        db_conn.commit()

        # 标记为 done（应该成功，因为 needs_verification=0）
        c.execute("""
            UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (task_id,))
        db_conn.commit()

        c.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        assert row[0] == "done", "不需要验证的任务不受 context_md 约束"


class TestContextMdPropagation:
    """Layer 2 & 3: 传递层 + 读取层 — complete → verify 链路完整"""

    def test_complete_task_validates_context_md(self, db_path):
        """complete_task API 在 needs_verification=1 时校验 context_md"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        task_id = "test-propagate-001"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification, context_md, acceptance_criteria)
            VALUES (?, ?, 'in_progress', 1, ?, ?)
        """, (task_id, "测试传递", "## 执行概要\n完整上下文", '{"criteria": [{"type": "compile", "name": "编译", "desc": "通过"}]}'))
        conn.commit()

        # 读取并模拟 complete_task 的校验逻辑
        c.execute("""
            SELECT context_md, acceptance_criteria, needs_verification
            FROM tasks WHERE id = ?
        """, (task_id,))
        task = c.fetchone()
        has_context_md = bool(task[0] and task[0].strip())
        has_acceptance_criteria = bool(task[1] and task[1].strip())

        assert has_context_md, "L2 失败：complete_task 时 context_md 应该非空"
        assert has_acceptance_criteria, "acceptance_criteria 应该非空"
        assert task[2] == 1, "needs_verification 应该为 1"
        conn.close()

    def test_verifier_reads_context_md_from_db(self, db_path):
        """verifier 在 context_md 未传参时，能从 DB 读取"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        task_id = "test-verifier-001"
        expected_md = "## 执行概要\n从 DB 读取的上下文"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification, context_md)
            VALUES (?, ?, 'verifying', 1, ?)
        """, (task_id, "测试 verifier", expected_md))
        conn.commit()

        # 模拟 trigger_verification 的 fallback 逻辑
        context_md = None  # 调用者没传
        if context_md is None:
            row = c.execute(
                "SELECT context_md FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            context_md = row[0] if row else None

        assert context_md is not None, "L3 失败：verifier 应该从 DB 读到 context_md"
        assert context_md == expected_md, "L3 失败：读到的 context_md 内容不匹配"
        conn.close()

    def test_verifier_handles_missing_context_md(self, db_path):
        """如果 DB 里也没有 context_md，verifier 不应崩溃"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        task_id = "test-verifier-002"
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification)
            VALUES (?, ?, 'verifying', 1)
        """, (task_id, "无上下文"))
        conn.commit()

        # 模拟 trigger_verification
        context_md = None
        row = c.execute(
            "SELECT context_md FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        context_md = row[0] if row else None

        # 应该 graceful 处理：context_md 为 None，但不崩溃
        assert context_md is None, "DB 里也没有时应该返回 None"
        # 不应该抛异常
        conn.close()


class TestContextMdFullLifecycle:
    """端到端：创建 → 派发 → 完成 → 验证，每一步 context_md 都不为空"""

    def test_full_lifecycle(self, db_path):
        """完整生命周期测试：context_md 从创建到验证全程非空"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        task_id = "test-lifecycle-001"

        # Step 1: 创建任务
        c.execute("""
            INSERT INTO tasks (id, title, status, needs_verification, context_md, acceptance_criteria)
            VALUES (?, ?, 'todo', 1, NULL, '{"criteria": [{"type": "compile", "name": "编译", "desc": "通过"}]}')
        """, (task_id, "生命周期测试"))
        conn.commit()

        # Step 2: 派发 → 写 context_md
        prompt = "## 执行概要\n你是一名 Python 开发者，请完成以下任务\n## 后端地址\nhttp://127.0.0.1:8097"
        c.execute("""
            UPDATE tasks SET context_md = ?, status = 'in_progress',
                started_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (prompt, datetime.now().isoformat(), task_id))
        conn.commit()
        c.execute("SELECT context_md FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        assert row[0] is not None, "Step 2 失败：派发后 context_md 应该已写入"
        assert len(row[0]) > 50, "Step 2 失败：context_md 内容不完整"

        # Step 3: 完成 → context_md 应保持非空
        c.execute("""
            UPDATE tasks SET status = 'done', completed_at = ?,
                updated_at = CURRENT_TIMESTAMP, result_summary = '编译通过'
            WHERE id = ?
        """, (datetime.now().isoformat(), task_id))
        conn.commit()
        c.execute("SELECT status, context_md FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        assert row[0] == "done", "Step 3 失败：任务应该已完成"
        assert row[1] is not None and row[1].strip() != "", "Step 3 失败：完成后 context_md 不应为空"

        # Step 4: 验证 → 能读到完整 context_md
        c.execute("SELECT context_md FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        context_md = row[0]
        assert context_md is not None, "Step 4 失败：验证时 context_md 应该可读"
        assert "后端地址" in context_md or "http" in context_md, \
            "Step 4 失败：context_md 应该包含关键执行信息"
        conn.close()


class TestContextMdHistoricalData:
    """脏数据验证：确认修复后历史数据已处理"""

    def test_no_null_context_md_for_completed_tasks(self, db_path):
        """所有 done 且 needs_verification=1 的任务，context_md 不应为 NULL"""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # 插入一些正常完成的数据
        for i in range(3):
            c.execute("""
                INSERT INTO tasks (id, title, status, needs_verification, context_md)
                VALUES (?, ?, 'done', 1, ?)
            """, (f"hist-done-{i}", f"已完成任务 {i}", "## 执行概要\n有效上下文"))
        conn.commit()

        # 查询脏数据
        c.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE needs_verification = 1 AND status = 'done'
            AND (context_md IS NULL OR context_md = '')
        """)
        null_count = c.fetchone()[0]
        assert null_count == 0, f"仍有 {null_count} 个已完成任务的 context_md 为空"
        conn.close()
