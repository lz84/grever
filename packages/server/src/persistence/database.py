"""
Grever Reins 数据库管理器
提供数据库初始化、迁移、连接管理
"""

from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from persistence.base import DatabaseConfig

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: DatabaseConfig):
        self._config = config
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._session: Optional[Session] = None  # facade session for ORM operations
    
    def get_session(self) -> Session:
        """创建并返回一个新的 SQLAlchemy Session"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory()
    
    @property
    def _facade_session(self) -> Session:
        """获取或创建 facade session（共享 session 用于 ORM 操作）"""
        if self._session is None:
            self._session = self.get_session()
        return self._session
    
    def query(self, *entities):
        """便捷查询方法，复用 facade session"""
        return self._facade_session.query(*entities)
    
    def add(self, obj):
        """添加对象到 facade session"""
        self._facade_session.add(obj)
    
    def commit(self):
        """提交 facade session 的更改"""
        if self._session is not None:
            self._session.commit()
    
    def close(self):
        """关闭 facade session 并释放引擎"""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        if self._engine:
            self._engine.dispose()
            self._engine = None
    
    @property
    def engine(self) -> Engine:
        """获取数据库引擎"""
        if self._engine is None:
            engine_kwargs = {
                "echo": False,
                "connect_args": {"check_same_thread": False} if self._config.provider == "sqlite" else {},
            }
            # SQLite 使用 StaticPool，不支持 pool_size/max_overflow
            if self._config.provider == "sqlite":
                engine_kwargs["poolclass"] = __import__("sqlalchemy.pool", fromlist=["StaticPool"]).StaticPool
            else:
                engine_kwargs["pool_size"] = self._config.pool_size
                engine_kwargs["max_overflow"] = self._config.max_overflow
            
            self._engine = create_engine(
                self._config.connection_string,
                **engine_kwargs,
            )
        return self._engine
    
    def create_tables(self):
        """创建所有表"""
        from persistence.tables import metadata
        metadata.create_all(self.engine)
    
    def drop_tables(self):
        """删除所有表（仅用于测试）"""
        from persistence.tables import metadata
        metadata.drop_all(self.engine)
