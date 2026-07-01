#!/usr/bin/env python3
"""
Grever 系统初始化脚本

功能：
1. 检查前置依赖（Python 版本、pip）
2. 自动配置 .env 文件（自动推导 SQLITE_PATH）
3. 安装 Python 依赖
4. 确保数据库目录存在
5. 创建数据库表
6. 可选：灌入/重置/修复演示数据

用法：
    cd packages/server
    python scripts/init_grever.py          # 基本初始化
    python scripts/init_grever.py --seed   # 初始化 + 灌入演示数据
    python scripts/init_grever.py --reset  # 重置演示数据（不删表）
    python scripts/init_grever.py --dry-run  # 预览会做什么
    python scripts/init_grever.py --fix    # 修复数据质量问题
"""

import os
import sys
import shutil
from pathlib import Path

# 添加 src 到路径（供 seed/fix 模块使用）
_scripts_dir = Path(__file__).resolve().parent
_package_dir = _scripts_dir.parent  # packages/server
_project_root = _package_dir.parent.parent  # agents-nexus (project root)
_src_dir = _package_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))


# ============================================================
# 颜色输出（纯 ASCII 符号，Windows GBK 兼容）
# ============================================================
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

def ok(msg):
    print(f"  {GREEN}[OK]{RESET} {msg}")

def warn(msg):
    print(f"  {YELLOW}[!]{RESET} {msg}")

def fail(msg):
    print(f"  {RED}[FAIL]{RESET} {msg}")

def step(msg):
    print(f"\n{BOLD}[{CYAN}Step{RESET}] {msg}")


# ============================================================
# 前置检查
# ============================================================
def check_prerequisites():
    step("检查前置依赖")

    # Python 版本
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        fail(f"Python 版本需要 >= 3.11，当前 {major}.{minor}")
        return False
    ok(f"Python {major}.{minor}")

    # pip
    try:
        import pip  # noqa: F401
        ok("pip 已安装")
    except ImportError:
        fail("pip 未安装，请先安装 pip")
        return False

    return True


# ============================================================
# 配置 .env 文件
# ============================================================
def setup_env(force=False):
    step("配置 .env 文件")

    env_file = _project_root / ".env"
    template_file = _project_root / ".env.template"

    # 确定数据库路径
    db_dir = _project_root / "data"
    db_path = db_dir / "reins.db"

    if env_file.exists() and not force:
        # 检查 .env 是否已有有效配置
        try:
            content = env_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = env_file.read_text(encoding="gbk", errors="ignore")
        if "SQLITE_PATH=" in content:
            # 提取现有路径
            for line in content.splitlines():
                if line.startswith("SQLITE_PATH="):
                    val = line.split("=", 1)[1].strip()
                    if val and val != '""':
                        ok(f".env 已存在，数据库路径: {val}")
                        return True
        warn(".env 已存在但可能未正确配置")
        # 非交互模式：跳过而不是问用户
        warn("跳过 .env 配置（如需覆盖请加 --force）")
        return False

    # 读取模板生成 .env
    if template_file.exists():
        template = template_file.read_text(encoding="utf-8")
    else:
        # 回退：手动构建
        template = """# Grever Reins 服务配置
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
SQLITE_PATH=
GREVER_BASE_URL=http://127.0.0.1:8096
LOG_LEVEL=info
"""

    # 替换占位符
    env_content = template
    for line in template.splitlines():
        if line.startswith("SQLITE_PATH="):
            # 替换为实际路径
            old_line = line
            new_line = f"SQLITE_PATH={db_path}"
            env_content = env_content.replace(old_line, new_line)

    env_file.write_text(env_content, encoding="utf-8")
    ok(f".env 已创建: {env_file}")
    ok(f"数据库路径: {db_path}")

    # 确保 data 目录存在
    db_dir.mkdir(parents=True, exist_ok=True)
    ok(f"data 目录: {db_dir}")

    return True


# ============================================================
# 安装依赖
# ============================================================
def install_dependencies():
    step("安装 Python 依赖")

    requirements = _project_root / "config" / "requirements.txt"
    pyproject = _project_root / "pyproject.toml"

    if not requirements.exists() and not pyproject.exists():
        # 尝试其他常见位置
        for p in [
            _project_root / "requirements.txt",
            _package_dir / "requirements.txt",
            _package_dir / "src" / "requirements.txt",
        ]:
            if p.exists():
                requirements = p
                break
        else:
            fail("未找到 requirements.txt 或 pyproject.toml")
            return False

    print(f"  依赖文件: {requirements}")

    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements), "-q"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # pip install 可能有 warning，但不一定是错误
        if "ERROR" in result.stderr.upper():
            fail("依赖安装失败")
            print(result.stderr[:500])
            return False

    ok("依赖安装完成")
    return True


# ============================================================
# 创建数据库表
# ============================================================
def create_tables():
    step("创建数据库表")

    db_path = _get_db_path()

    # 确保目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ok(f"数据库路径: {db_path}")

    if not db_path.exists():
        # 创建空数据库文件
        db_path.touch()
        ok("数据库文件已创建")

    # 设置 PYTHONPATH 并导入
    if str(_src_dir) not in sys.path:
        sys.path.insert(0, str(_src_dir))

    # 尝试导入迁移模块执行建表
    try:
        from persistence.config import DatabaseConfig
        from persistence.database import DatabaseManager

        config = DatabaseConfig(provider="sqlite", path=str(db_path))
        manager = DatabaseManager(config)

        # 检查是否已有表
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()

        if len(tables) > 2:  # sqlite_sequence + schema_migrations 等
            ok(f"数据库已存在 {len(tables)} 张表，跳过建表")
        else:
            # 执行建表
            try:
                manager.create_tables()
                cursor2 = sqlite3.connect(str(db_path)).cursor()
                cursor2.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables2 = [r[0] for r in cursor2.fetchall()]
                ok(f"建表完成，共 {len(tables2)} 张表")
            except Exception as me:
                warn(f"建表执行有警告: {me}")
                ok("继续（可能表已存在）")

        return True

    except Exception as e:
        warn(f"数据库模块导入失败: {e}")
        # 回退：只要数据库文件存在就认为 OK
        if db_path.exists():
            ok("数据库文件已存在，跳过建表")
            return True
        fail("数据库初始化失败")
        return False


# ============================================================
# 灌入演示数据（可选）
# ============================================================
def seed_data():
    step("灌入演示数据（软件开发场景）")

    try:
        from scripts.seed.seed_software_dev import seed_database
        db_path = _get_db_path()
        seed_database(db_path)
        ok("演示数据灌入完成")
    except Exception as e:
        fail(f"演示数据灌入失败: {e}")
        raise


# ============================================================
# 重置演示数据
# ============================================================
def reset_demo_data():
    step("重置演示数据（保留 schema）")

    try:
        import sqlite3
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # 删除已知演示数据的 goal（按 ID）
        demo_goal_ids = [
            "goal-ecommerce-001",
            "goal-cicd-001",
            "goal-tech-debt-001",
        ]
        placeholders = ",".join("?" for _ in demo_goal_ids)

        c.execute(f"DELETE FROM tasks WHERE goal_id IN ({placeholders})", demo_goal_ids)
        c.execute(f"DELETE FROM projects WHERE goal_id IN ({placeholders})", demo_goal_ids)
        c.execute(f"DELETE FROM goals WHERE id IN ({placeholders})", demo_goal_ids)

        # 删除演示场景
        c.execute("DELETE FROM scenarios WHERE name LIKE '%电商%' OR name LIKE '%CI/CD%' OR name LIKE '%技术债%' OR name LIKE '%ecommerce%' OR name LIKE '%cicd%' OR name LIKE '%tech-debt%'")

        conn.commit()
        ok("演示数据重置完成")
        conn.close()
    except Exception as e:
        fail(f"演示数据重置失败: {e}")
        raise


# ============================================================
# 修复数据质量问题
# ============================================================
def fix_data_quality():
    step("修复数据质量问题")

    try:
        from scripts.fix_data_quality import fix_data_quality as _fix
        db_path = _get_db_path()
        _fix(db_path)
        ok("数据质量修复完成")
    except Exception as e:
        fail(f"数据质量修复失败: {e}")
        raise


# ============================================================
# 预览（不实际执行）
# ============================================================
def dry_run():
    step("预览 -- 以下操作会被执行（不含实际变更）")

    db_path = _get_db_path()
    ok(f"数据库路径: {db_path}")
    ok(f"前置检查: Python >= 3.11, pip 可用")
    ok(f".env 配置: 检查/生成")
    ok(f"依赖安装: pip install -r requirements.txt")
    ok(f"建表: 执行所有未执行的迁移（{_count_pending_migrations()} 个待执行）")
    print("\n  如需执行，请去掉 --dry-run 参数重新运行")


# ============================================================
# 辅助函数
# ============================================================
def _get_db_path() -> Path:
    """从环境变量或 .env 获取数据库路径"""
    env_path = _project_root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("SQLITE_PATH="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    p = Path(val)
                    return p if p.is_absolute() else _project_root / val
    return _project_root / "data" / "reins.db"


def _count_pending_migrations() -> int:
    """统计待执行的迁移数量"""
    try:
        import sqlite3
        db_path = _get_db_path()
        migration_dir = _src_dir / "persistence" / "migrations"
        if not migration_dir.exists():
            return 0
        if not db_path.exists():
            files = [f for f in migration_dir.iterdir() if f.suffix in (".sql",) and f.stem[0].isdigit()]
            return len(files)
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM schema_migrations")
        done = c.fetchone()[0] or 0
        conn.close()
        files = [f for f in migration_dir.iterdir() if f.suffix in (".sql",) and f.stem[0].isdigit()]
        return max(0, len(files) - done)
    except Exception:
        return 0


# ============================================================
# 主流程
# ============================================================
def main():
    print(f"\n{BOLD}{'='*50}")
    print(f"  {CYAN}Grever 系统初始化{RESET}")
    print(f"{'='*50}{RESET}\n")

    import argparse
    parser = argparse.ArgumentParser(description="Grever 系统初始化")
    parser.add_argument("--seed", action="store_true", help="灌入演示数据")
    parser.add_argument("--reset", action="store_true", help="重置演示数据（保留 schema）")
    parser.add_argument("--dry-run", action="store_true", help="预览会做什么，不执行")
    parser.add_argument("--fix", action="store_true", help="修复数据质量问题")
    parser.add_argument("--force", action="store_true", help="强制覆盖现有 .env 文件")
    args = parser.parse_args()

    # --dry-run: 只做预览，不执行任何实际操作
    if args.dry_run:
        dry_run()
        sys.exit(0)

    # 1. 前置检查
    if not check_prerequisites():
        sys.exit(1)

    # 2. 配置 .env
    if not setup_env(force=args.force):
        pass  # 用户选择跳过，继续

    # 3. 安装依赖
    if not install_dependencies():
        warn("依赖安装可能有警告，继续...")

    # 4. 创建数据库表
    if not create_tables():
        fail("数据库表创建失败，无法继续")
        sys.exit(1)

    # 5. 可选操作（互斥：--reset / --seed / --fix）
    if args.reset:
        reset_demo_data()
        sys.exit(0)
    elif args.seed:
        seed_data()
    elif args.fix:
        fix_data_quality()
        sys.exit(0)

    print(f"\n{BOLD}{'='*50}")
    print(f"  {GREEN}初始化完成！{RESET}")
    print(f"{'='*50}{RESET}\n")
    print("启动命令：")
    print(f"  cd packages/server")
    print(f"  PYTHONPATH=src python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8096")
    print(f"\n访问：")
    print(f"  API 文档: http://localhost:8096/docs")
    print(f"  API 服务: http://localhost:8096/api/v1/tasks")
    print()


if __name__ == "__main__":
    main()
