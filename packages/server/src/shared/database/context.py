"""
数据库连接上下文管理器
提供便捷的连接获取方式
"""

import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from .pool import ConnectionPool, get_pool
from shared.common.exceptions import DatabaseException, ErrorCode


@asynccontextmanager
async def acquire_connection(
    pool_name: str = "default",
    timeout: Optional[int] = None,
):
    """
    从连接池获取连接的异步上下文管理器
    
    使用方式:
    ```python
    async with acquire_connection() as conn:
        result = await conn.execute("SELECT * FROM users")
    ```
    
    :param pool_name: 连接池名称
    :param timeout: 获取连接超时（秒）
    :yield: 数据库连接
    """
    pool = get_pool(pool_name)
    
    if pool is None:
        raise DatabaseException(
            message=f"Connection pool '{pool_name}' not found",
            code=ErrorCode.DB_CONNECTION_ERROR,
        )
    
    conn = await pool.acquire(timeout=timeout)
    try:
        yield conn
    finally:
        await pool.release(conn)


class PoolContext:
    """
    连接池上下文管理器
    用于管理连接池的生命周期
    """
    
    def __init__(self, pool: ConnectionPool):
        """
        初始化连接池上下文
        
        :param pool: 连接池实例
        """
        self.pool = pool
        self._conn = None
    
    async def __aenter__(self):
        """进入上下文"""
        self._conn = await self.pool.acquire()
        return self._conn
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self._conn:
            await self.pool.release(self._conn)
            self._conn = None
        
        return False


@asynccontextmanager
async def pooled_connection(
    pool_name: str = "default",
    timeout: Optional[int] = None,
):
    """
    同步连接获取的异步上下文管理器（兼容性包装）
    
    与 acquire_connection 功能相同，提供别名
    """
    async with acquire_connection(pool_name, timeout) as conn:
        yield conn
