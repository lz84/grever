"""
数据库会话管理

提供 SQLAlchemy 会话生成器，供 FastAPI 依赖注入使用
所有配置来自 database.config（统一配置中心）
"""

from sqlalchemy.orm import sessionmaker, scoped_session
from typing import Optional, Generator
from sqlalchemy.orm import Session

from shared.database.models import Base
from shared.database.config import get_engine, DB_CONFIG


class DatabaseSessionManager:
    """
    数据库会话管理器
    
    提供:
    - SQLAlchemy Session 生成
    - 数据库初始化
    - 会话生命周期管理
    """
    
    def __init__(self):
        self._engine = get_engine()
        self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        self._Session = scoped_session(self._SessionLocal)
        
        # 初始化数据库表
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        from shared.database import models
        Base.metadata.create_all(bind=self._engine)
    
    def get_session(self):
        """获取数据库会话"""
        return self._Session()
    
    def close_session(self):
        """关闭当前会话"""
        self._Session.remove()
    
    def close_engine(self):
        """关闭数据库引擎"""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# 全局会话管理器实例
_database_manager: Optional[DatabaseSessionManager] = None


def get_database_manager() -> DatabaseSessionManager:
    """获取全局数据库会话管理器"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseSessionManager()
    return _database_manager


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI 依赖项 - 获取数据库会话
    
    使用方式:
    ```python
    @app.get("/items")
    def read_items(db: Session = Depends(get_db_session)):
        ...
    ```
    """
    db = get_database_manager().get_session()
    try:
        yield db
    finally:
        get_database_manager().close_session()
