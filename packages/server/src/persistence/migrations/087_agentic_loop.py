"""
Migration 087: Agentic Loop 数据库结构扩展

新增表：
- capability_tags（能力标签，含 standards 和 parent_tag）
- planning_sessions（规划讨论记录）
- goal_sessions（Agent 平台会话日志）
- verification_reports（Project/Goal 级统筹验证结果）

字段新增：
- tasks: self_review_count, self_review_report, dispatch_attempt, loop_state, loop_context
- agents: domain_tags, verification_capabilities
- goals: decomposition_config
- knowledge_base: auto_extracted, source_task_id, knowledge_type

数据种子：
- 初始能力标签：开发、python开发、前端开发
"""
import json
import os
import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.environ.get("SQLITE_PATH", r"D:\work\research\agents-nexus\data\reins.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")

def safe_exec(sql, desc=""):
    try:
        conn.execute(sql)
        conn.commit()
        print(f"OK {desc}")
        return True
    except Exception as e:
        print(f"  {desc}: {e}")
        return False

# ============================================================
# 1. 新建 capability_tags 表
# ============================================================
safe_exec("""
    CREATE TABLE IF NOT EXISTS capability_tags (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        parent_tag TEXT REFERENCES capability_tags(id),
        standards TEXT DEFAULT '[]',
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
    )
""", "capability_tags table created")

# ============================================================
# 2. 新建 planning_sessions 表
# ============================================================
safe_exec("""
    CREATE TABLE IF NOT EXISTS planning_sessions (
        id TEXT PRIMARY KEY,
        goal_id TEXT REFERENCES goals(id),
        trigger_type TEXT DEFAULT 'goal_creation',
        input_type TEXT DEFAULT 'text',
        input_content TEXT,
        document_refs TEXT DEFAULT '[]',
        discussion_log TEXT DEFAULT '[]',
        draft_versions TEXT DEFAULT '[]',
        status TEXT DEFAULT 'drafting',
        confirmed_plan TEXT,
        decision_rationale TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        confirmed_at INTEGER
    )
""", "planning_sessions table created")

# ============================================================
# 3. 新建 goal_sessions 表
# ============================================================
safe_exec("""
    CREATE TABLE IF NOT EXISTS goal_sessions (
        id TEXT PRIMARY KEY,
        goal_id TEXT REFERENCES goals(id),
        session_id TEXT NOT NULL,
        session_type TEXT DEFAULT 'coordinator',
        platform TEXT DEFAULT 'openclaw',
        messages TEXT DEFAULT '[]',
        status TEXT DEFAULT 'active',
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        closed_at INTEGER
    )
""", "goal_sessions table created")

# ============================================================
# 4. 新建 verification_reports 表
# ============================================================
safe_exec("""
    CREATE TABLE IF NOT EXISTS verification_reports (
        id TEXT PRIMARY KEY,
        level TEXT NOT NULL,
        target_id TEXT NOT NULL,
        verifier_id TEXT,
        round INTEGER DEFAULT 1,
        verdict TEXT NOT NULL,
        summary TEXT,
        task_results TEXT DEFAULT '[]',
        gaps TEXT DEFAULT '[]',
        recommendations TEXT DEFAULT '[]',
        remedial_tasks TEXT DEFAULT '[]',
        raw_context TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
    )
""", "verification_reports table created")

# ============================================================
# 5. tasks 表新增字段
# ============================================================
for col, ctype in [
    ("self_review_count", "INTEGER DEFAULT 0"),
    ("self_review_report", "TEXT DEFAULT '{}'"),
    ("dispatch_attempt", "INTEGER DEFAULT 0"),
    ("loop_state", "TEXT DEFAULT 'idle'"),
    ("loop_context", "TEXT DEFAULT '{}'"),
]:
    safe_exec(f"ALTER TABLE tasks ADD COLUMN {col} {ctype}", f"tasks.{col}")

# ============================================================
# 6. agents 表新增字段
# ============================================================
for col, ctype in [
    ("domain_tags", "TEXT DEFAULT '[]'"),
    ("verification_capabilities", "TEXT DEFAULT '[]'"),
]:
    safe_exec(f"ALTER TABLE agents ADD COLUMN {col} {ctype}", f"agents.{col}")

# ============================================================
# 7. goals 表新增字段
# ============================================================
safe_exec("ALTER TABLE goals ADD COLUMN decomposition_config TEXT DEFAULT '{}'", "goals.decomposition_config")

# ============================================================
# 8. knowledge_base 表新增字段
# ============================================================
for col, ctype in [
    ("auto_extracted", "INTEGER DEFAULT 0"),
    ("source_task_id", "TEXT"),
    ("knowledge_type", "TEXT"),
]:
    safe_exec(f"ALTER TABLE knowledge_base ADD COLUMN {col} {ctype}", f"knowledge_base.{col}")

# ============================================================
# 9. 插入初始能力标签数据（idempotent）
# ============================================================
now = int(__import__('time').time())

initial_tags = [
    ("tag-dev-001", "开发", None, [
        "编译/语法检查通过",
        "无 console.error 或 traceback",
        "依赖安装正确"
    ]),
    ("tag-python-001", "python开发", "tag-dev-001", [
        "py_compile 通过",
        "pytest 基础测试通过",
        "符合 PEP 8"
    ]),
    ("tag-frontend-001", "前端开发", "tag-dev-001", [
        "tsc 编译 0 errors",
        "页面不白屏，关键元素可见",
        "浏览器 console 无报错"
    ]),
]

for tag_id, name, parent, standards in initial_tags:
    try:
        conn.execute(
            "INSERT OR IGNORE INTO capability_tags (id, name, parent_tag, standards, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tag_id, name, parent, json.dumps(standards, ensure_ascii=False), now, now)
        )
        conn.commit()
        print(f"OK capability_tag data: {name}")
    except Exception as e:
        print(f"  capability_tag data {name}: {e}")

# ============================================================
# 10. 验证
# ============================================================
cur = conn.cursor()

# Verify capability_tags
cur.execute("PRAGMA table_info(capability_tags)")
cols = {r[1] for r in cur.fetchall()}
assert {'id', 'name', 'parent_tag', 'standards'} <= cols, f"capability_tags missing cols: {cols}"
print("OK capability_tags schema verified")

# Verify tasks
cur.execute("PRAGMA table_info(tasks)")
cols = {r[1] for r in cur.fetchall()}
for c in ['self_review_count', 'self_review_report', 'dispatch_attempt', 'loop_state', 'loop_context']:
    assert c in cols, f"tasks missing {c}"
print("OK tasks schema verified")

# Verify agents
cur.execute("PRAGMA table_info(agents)")
cols = {r[1] for r in cur.fetchall()}
for c in ['domain_tags', 'verification_capabilities']:
    assert c in cols, f"agents missing {c}"
print("OK agents schema verified")

# Verify data
cur.execute("SELECT id, name, parent_tag FROM capability_tags")
tags = cur.fetchall()
print(f"OK capability_tags data: {len(tags)} tags")
for t in tags:
    print(f"  - {t[1]} (parent: {t[2] or 'none'})")

conn.close()
print("\nMigration 087 applied successfully!")
