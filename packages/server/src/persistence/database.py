"""
Nexus Reins 数据库管理器
提供数据库初始化、迁移、连接管理
"""

from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from persistence.base import DatabaseConfig

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: DatabaseConfig):
        self._config = config
        self._engine: Optional[Engine] = None
    
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
    
    def close(self):
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
