"""
Sprint 123 Phase 6: 数据质量修复脚本

修复数据问题：
- goals.mode = NULL 或缺失
- tasks.verifier_agent_id = NULL

用法：
    cd packages/server
    python scripts/fix_data_quality.py
    python scripts/fix_data_quality.py --db-path /path/to/reins.db
"""

import os
import sys
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """从环境变量、.env 或默认路径获取数据库路径"""
    # 1. 命令行参数
    for i, arg in enumerate(sys.argv):
        if arg == '--db-path' and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])

    # 2. 环境变量
    env_path = os.environ.get('SQLITE_PATH')
    if env_path:
        p = Path(env_path)
        return p if p.is_absolute() else Path.cwd() / p

    # 3. .env 文件
    scripts_dir = Path(__file__).resolve().parent
    package_dir = scripts_dir.parent
    project_root = package_dir.parent.parent  # agents-nexus
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            content = env_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = env_file.read_text(encoding="gbk", errors="ignore")
        for line in content.splitlines():
            if line.strip().startswith("SQLITE_PATH="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    p = Path(val)
                    return p if p.is_absolute() else project_root / p

    # 4. 默认
    return project_root / "data" / "reins.db"


def fix_data_quality(db_path: Path):
    """修复数据质量问题（纯 sqlite3，不依赖 ORM）"""
    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        sys.exit(1)

    print(f"数据库路径: {db_path}")
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    print("\n开始修复数据质量问题...")

    # 1. 修复 goals.mode NULL 问题
    print("\n1. 修复 goals.mode 字段...")
    c.execute("SELECT COUNT(*) FROM goals WHERE mode IS NULL OR mode = ''")
    null_mode_count = c.fetchone()[0]

    if null_mode_count > 0:
        print(f"   发现 {null_mode_count} 个 goals 的 mode 字段为 NULL 或空")
        c.execute("UPDATE goals SET mode = 'engineering' WHERE mode IS NULL OR mode = ''")
        conn.commit()
        print(f"   已修复: {null_mode_count} 个 goals (mode=engineering)")
    else:
        print("   所有 goals 的 mode 字段正常")

    # 2. 修复 tasks.verifier_agent_id NULL 问题
    print("\n2. 修复 tasks.verifier_agent_id 字段...")
    c.execute("SELECT COUNT(*) FROM tasks WHERE verifier_agent_id IS NULL")
    no_verifier_count = c.fetchone()[0]

    if no_verifier_count > 0:
        print(f"   发现 {no_verifier_count} 个 tasks 缺少 verifier_agent_id")
        # 取第一个 agent 作为默认 verifier
        c.execute("SELECT id FROM agents LIMIT 1")
        row = c.fetchone()
        default_verifier = row[0] if row else 'system'
        c.execute(
            "UPDATE tasks SET verifier_agent_id = ? WHERE verifier_agent_id IS NULL",
            (default_verifier,)
        )
        conn.commit()
        print(f"   已修复: {no_verifier_count} 个 tasks (verifier={default_verifier})")
    else:
        print("   所有 tasks 都有 verifier_agent_id")

    # 3. 验证修复结果
    print("\n3. 验证修复结果...")
    c.execute("SELECT COUNT(*) FROM goals WHERE mode IS NULL OR mode = ''")
    final_null_mode = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tasks WHERE verifier_agent_id IS NULL")
    final_no_verifier = c.fetchone()[0]

    if final_null_mode == 0 and final_no_verifier == 0:
        print("   数据质量修复完成！")
        print(f"   - goals.mode NULL: {final_null_mode}")
        print(f"   - tasks.verifier_agent_id NULL: {final_no_verifier}")
    else:
        print("   部分问题未完全修复:")
        print(f"   - goals.mode NULL: {final_null_mode}")
        print(f"   - tasks.verifier_agent_id NULL: {final_no_verifier}")

    # 4. 统计当前数据
    print("\n4. 当前数据统计:")
    for table in ['goals', 'projects', 'tasks', 'agents']:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = c.fetchone()[0]
        print(f"   - {table}: {cnt}")

    conn.close()
    print(f"\n数据质量修复完成: {db_path}")


if __name__ == "__main__":
    db_path = get_db_path()
    fix_data_quality(db_path)
