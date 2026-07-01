"""
Grever Reins 数据库模块

提供 SQLAlchemy 数据库连接管理（ReinsServer ORM 专用）
所有配置来自 database.config（统一配置中心）

⚠️ 换数据库只需改 database/config.py
"""

from pathlib import Path
from typing import Generator, Optional
from sqlalchemy.orm import Session, sessionmaker

# 从统一配置中心获取
from shared.database.config import DB_CONFIG, get_engine
from persistence.database import DatabaseManager
from persistence.base import DatabaseConfig

# 公共 API
__all__ = [
    "DB_PATH",
    "get_db_manager",
    "get_db_session",
    "get_db",
    "init_db",
    "close_db",
]

# ============================================================
# DB_PATH 别名（从统一配置获取）
# ============================================================
if DB_CONFIG.provider == "sqlite":
    DB_PATH = DB_CONFIG.sqlite_path
else:
    DB_PATH = DB_CONFIG.url  # 非 SQLite 时返回连接字符串

# ============================================================
# 数据库管理器（懒加载单例）
# ============================================================
_DB_MANAGER: Optional[DatabaseManager] = None
_SESSION_LOCAL: Optional[sessionmaker[Session]] = None

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（懒加载单例）"""
    global _DB_MANAGER
    if _DB_MANAGER is None:
        config = DatabaseConfig(
            provider=DB_CONFIG.provider,
            path=DB_CONFIG.sqlite_path if DB_CONFIG.provider == "sqlite" else DB_CONFIG.url,
            host=DB_CONFIG.host,
            port=DB_CONFIG.port,
            database=DB_CONFIG.database,
            user=DB_CONFIG.user,
            password=DB_CONFIG.password,
        )
        _DB_MANAGER = DatabaseManager(config)
    return _DB_MANAGER

def get_db_session() -> Session:
    """获取数据库会话"""
    global _SESSION_LOCAL
    if _SESSION_LOCAL is None:
        engine = get_db_manager().engine
        _SESSION_LOCAL = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SESSION_LOCAL()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入用数据库会话
    
    使用简单 generator，兼容 Python 3.13 + FastAPI。
    finally 中关闭 session，FastAPI 会在响应序列化完成后再恢复 generator。
    """
    db = get_db_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """初始化数据库（创建表）"""
    get_db_manager().create_tables()

def close_db():
    """关闭数据库连接"""
    global _DB_MANAGER
    if _DB_MANAGER:
        _DB_MANAGER.close()
        _DB_MANAGER = None
