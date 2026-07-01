"""
Grever Reins Manager 基类
提供持久化支持
"""

from abc import ABC
from sqlalchemy import create_engine
from typing import Optional

class BaseManager(ABC):
    """Manager 基类"""
    
    def __init__(self, db_config=None, repository=None):
        self._db_config = db_config
        self._repository = repository
        self._engine = None
    
    def _init_engine(self):
        """初始化数据库引擎"""
        if self._db_config and self._engine is None:
            from persistence.base import DatabaseConfig
            if isinstance(self._db_config, DatabaseConfig):
                self._engine = create_engine(
                    self._db_config.connection_string,
                    pool_size=getattr(self._db_config, 'pool_size', 10),
                    max_overflow=getattr(self._db_config, 'max_overflow', 20),
                    echo=False,
                    connect_args={"check_same_thread": False} if self._db_config.provider == "sqlite" else {},
                )
                # 初始化仓库
                if self._repository:
                    self._repository._engine = self._engine
