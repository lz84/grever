"""系统初始化检查 — 从 server.py 拆分（server.py ≤ 50 行铁律）"""

import os
import sqlite3
import sys

from loguru import logger


def check_initialization(db_path: str) -> bool:
    """检查系统是否已初始化。返回 True 表示已初始化，False 表示需要初始化。"""
    issues = []

    if not os.path.exists(db_path):
        issues.append(f"数据库文件不存在: {db_path}")
    else:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0] for r in cursor.fetchall()}
            conn.close()

            core_tables = {"tasks", "goals", "projects", "agents", "schema_migrations"}
            missing = core_tables - tables
            if missing:
                issues.append(f"缺少核心数据表: {', '.join(sorted(missing))}")
        except Exception as e:
            issues.append(f"无法读取数据库: {e}")

    if issues:
        sep = "=" * 60
        _emit(f"\n{sep}\n  Grever 系统未初始化\n{sep}\n")
        for issue in issues:
            _emit(f"  {issue}\n")
        _emit(f"\n  请运行以下命令完成初始化：\n"
              f"  cd packages/server\n"
              f"  python scripts/init_grever.py\n\n"
              f"  如需灌入演示数据，添加 --seed 参数：\n"
              f"  python scripts/init_grever.py --seed\n"
              f"{sep}\n")
        return False

    return True


def _emit(msg: str) -> None:
    """输出到 stderr（启动前 logger 未初始化，用 print 到 stderr）"""
    print(msg, file=sys.stderr, end="")
