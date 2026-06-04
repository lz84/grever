"""
数据库连接池实现
提供高性能、可靠的数据库连接池管理
"""

import asyncio
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from typing import Optional, Any, Dict, List, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from .config import PoolConfig
from shared.common.exceptions import DatabaseException, ErrorCode


logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """连接池指标"""
    active_connections: int = 0
    idle_connections: int = 0
    waiting_threads: int = 0
    total_connections_created: int = 0
    total_connections_closed: int = 0
    connection_errors: int = 0
    reconnect_count: int = 0
    last_validation_time: Optional[datetime] = None
    last_reconnect_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'active_connections': self.active_connections,
            'idle_connections': self.idle_connections,
            'waiting_threads': self.waiting_threads,
            'total_connections_created': self.total_connections_created,
            'total_connections_closed': self.total_connections_closed,
            'connection_errors': self.connection_errors,
            'reconnect_count': self.reconnect_count,
            'last_validation_time': self.last_validation_time.isoformat() if self.last_validation_time else None,
            'last_reconnect_time': self.last_reconnect_time.isoformat() if self.last_reconnect_time else None,
        }


class PooledConnection:
    """
    SQLite 数据库连接包装器
    
    提供统一的连接接口，封装 sqlite3 连接的创建、执行和关闭
    """
    
    def __init__(self, connection_id: str, db_path: str):
        self.connection_id = connection_id
        self.db_path = db_path
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self._connection: Optional[sqlite3.Connection] = None
        self._ensure_connection()
    
    def _ensure_connection(self):
        """确保连接已建立"""
        if self._connection is None or self._is_closed():
            self._connection = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None,  # 自动提交
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            # 启用外键支持
            self._connection.execute("PRAGMA foreign_keys = ON")
            self.last_used_at = datetime.now()
    
    def _is_closed(self) -> bool:
        """检查连接是否已关闭"""
        # sqlite3 没有 ping 方法，尝试执行查询
        try:
            self._connection.execute("SELECT 1")
            return False
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            return True
    
    def execute(self, query: str, params: tuple = None) -> Any:
        """执行 SQL 查询"""
        self._ensure_connection()
        self.last_used_at = datetime.now()
        
        cursor = self._connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # 根据查询类型返回不同结果
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            elif query.strip().upper().startswith("INSERT") or \
                 query.strip().upper().startswith("UPDATE") or \
                 query.strip().upper().startswith("DELETE"):
                self._connection.commit()
                return cursor.rowcount
            return None
        finally:
            cursor.close()
    
    def executemany(self, query: str, params_list: List[tuple]) -> int:
        """批量执行 SQL 语句"""
        self._ensure_connection()
        self.last_used_at = datetime.now()
        
        cursor = self._connection.cursor()
        try:
            cursor.executemany(query, params_list)
            self._connection.commit()
            return len(params_list)
        finally:
            cursor.close()
    
    def close(self):
        """关闭连接"""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None
    
    def is_valid_connection(self) -> bool:
        """检查连接是否有效"""
        if self._connection is None:
            return False
        return not self._is_closed()


class ConnectionPool:
    """
    数据库连接池
    
    提供:
    - 连接复用：避免频繁创建/销毁连接
    - 健康检查：定期检查连接有效性
    - 自动重连：连接断开时自动重连
    - 熔断保护：数据库不可用时熔断
    - 指标监控：连接池使用指标
    """
    
    def __init__(self, config: PoolConfig):
        """
        初始化连接池
        
        :param config: 连接池配置
        """
        self.config = config
        self.pool_id = f"pool-{uuid.uuid4().hex[:8]}"
        
        # 提取数据库路径（SQLite 只需要一个路径）
        self.db_path = self._get_db_path()
        
        # 连接池状态
        self._idle_connections: List[PooledConnection] = []
        self._active_connections: Dict[str, PooledConnection] = {}
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        
        # 运行状态
        self._running = False
        self._health_check_task: Optional[threading.Thread] = None
        self._reconnect_task: Optional[threading.Thread] = None
        
        # 指标
        self._metrics = PoolMetrics()
        
        # 熔断器状态
        self._circuit_breaker_state = "closed"  # closed, open, half-open
        self._circuit_breaker_failures = 0
        self._circuit_breaker_successes = 0
        
        # 初始化连接池
        self._initialize()
    
    def _get_db_path(self) -> str:
        """
        根据配置获取数据库路径
        
        SQLite 使用文件路径，这里从配置中提取
        """
        # 对于 SQLite，database 字段应该是完整的文件路径
        if self.config.database:
            return self.config.database
        # 默认路径
        return "data/nexus.db"
    
    def _initialize(self):
        """初始化连接池"""
        # 创建最小连接数
        for _ in range(self.config.pool_min_size):
            try:
                conn = self._create_connection()
                self._idle_connections.append(conn)
                self._metrics.total_connections_created += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
                self._metrics.connection_errors += 1
        
        self._running = True
        
        # 启动健康检查线程
        if self.config.health_check_enabled:
            self._start_health_check()
        
        logger.info(
            f"Connection pool initialized: min={self.config.pool_min_size}, max={self.config.pool_max_size}",
            extra={"pool_id": self.pool_id}
        )
    
    def _create_connection(self) -> PooledConnection:
        """
        创建新连接
        
        :return: 新创建的连接
        :raises DatabaseException: 连接创建失败
        """
        try:
            connection_id = f"conn-{uuid.uuid4().hex[:8]}"
            conn = PooledConnection(connection_id, self.db_path)
            logger.debug(f"Created new SQLite connection: {connection_id}")
            return conn
        except Exception as e:
            self._metrics.connection_errors += 1
            raise DatabaseException(
                message=f"Failed to create connection: {e}",
                code=ErrorCode.DB_CONNECTION_ERROR,
                original_error=e,
            )
    
    def _validate_connection(self, conn: PooledConnection) -> bool:
        """
        验证连接是否有效
        
        :param conn: 待验证的连接
        :return: 连接是否有效
        """
        try:
            if not conn.is_valid_connection():
                return False
            
            # 执行健康检查查询
            if self.config.validation_query:
                conn.execute(self.config.validation_query)
                self._metrics.last_validation_time = datetime.now()
                return True
            
            return True
            
        except Exception as e:
            logger.debug(f"Connection validation failed: {e}")
            return False
    
    async def acquire(self, timeout: Optional[int] = None) -> PooledConnection:
        """
        从连接池获取连接
        
        :param timeout: 获取连接超时（秒），None 表示使用配置值
        :return: 获取的连接
        :raises DatabaseException: 获取连接失败
        """
        timeout_ms = timeout * 1000 if timeout else self.config.connection_timeout
        
        start_time = time.time()
        max_wait = timeout_ms / 1000
        
        while True:
            # 检查熔断器
            if self._circuit_breaker_state == "open":
                raise DatabaseException(
                    message="Circuit breaker is open, database is unavailable",
                    code=ErrorCode.DB_POOL_EXHAUSTED,
                )
            
            with self._lock:
                # 尝试从空闲连接池获取
                if self._idle_connections:
                    conn = self._idle_connections.pop(0)
                    self._metrics.idle_connections -= 1
                    
                    # 验证连接有效性
                    if self.config.test_on_borrow and not self._validate_connection(conn):
                        logger.debug(f"Invalid connection, creating new one")
                        conn.close()
                        self._metrics.total_connections_closed += 1
                        continue
                    
                    # 标记为活动连接
                    self._active_connections[conn.connection_id] = conn
                    self._metrics.active_connections += 1
                    
                    if self.config.test_on_borrow:
                        self._metrics.last_validation_time = datetime.now()
                    
                    logger.debug(f"Acquired connection: {conn.connection_id}")
                    return conn
                
                # 检查是否可以创建新连接
                if len(self._active_connections) + len(self._idle_connections) < self.config.pool_max_size:
                    try:
                        conn = self._create_connection()
                        self._active_connections[conn.connection_id] = conn
                        self._metrics.total_connections_created += 1
                        self._metrics.active_connections += 1
                        
                        if self.config.test_on_borrow:
                            self._metrics.last_validation_time = datetime.now()
                        
                        logger.debug(f"Created and acquired new connection: {conn.connection_id}")
                        return conn
                    except DatabaseException as e:
                        # 连接创建失败，尝试重试
                        logger.warning(f"Failed to create connection: {e}")
                
                # 需要等待
                self._metrics.waiting_threads += 1
                
                try:
                    # 等待条件变量
                    self._condition.wait(timeout=max_wait)
                finally:
                    self._metrics.waiting_threads -= 1
                
                # 检查是否超时
                elapsed = time.time() - start_time
                if elapsed >= max_wait:
                    raise DatabaseException(
                        message="Timeout waiting for connection",
                        code=ErrorCode.DB_CONNECTION_ERROR,
                    )
    
    async def release(self, conn: PooledConnection):
        """
        释放连接回连接池
        
        :param conn: 要释放的连接
        """
        with self._lock:
            # 从活动连接移除
            if conn.connection_id in self._active_connections:
                del self._active_connections[conn.connection_id]
                self._metrics.active_connections -= 1
            
            # 检查连接有效性
            if self.config.test_on_return and not self._validate_connection(conn):
                logger.debug(f"Invalid connection on return, closing")
                conn.close()
                self._metrics.total_connections_closed += 1
                self._metrics.connection_errors += 1
                return
            
            # 放回空闲连接池
            self._idle_connections.append(conn)
            self._metrics.idle_connections += 1
            
            # 通知等待的线程
            self._condition.notify()
            
            logger.debug(f"Released connection: {conn.connection_id}")
    
    @asynccontextmanager
    async def connection(self):
        """
        获取连接的上下文管理器
        
        使用方式:
        ```python
        async with pool.connection() as conn:
            result = await conn.execute("SELECT * FROM users")
        ```
        """
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)
    
    def _start_health_check(self):
        """启动健康检查线程"""
        def health_check_loop():
            while self._running:
                try:
                    self._check_idle_connections()
                except Exception as e:
                    logger.error(f"Health check error: {e}")
                
                time.sleep(self.config.idle_test_interval / 1000)
        
        self._health_check_task = threading.Thread(target=health_check_loop, daemon=True)
        self._health_check_task.start()
    
    def _check_idle_connections(self):
        """检查空闲连接"""
        with self._lock:
            current_time = time.time()
            idle_to_remove = []
            
            for conn in self._idle_connections:
                idle_time = (current_time - conn.last_used_at.timestamp()) * 1000
                
                # 检查空闲超时
                if idle_time > self.config.idle_timeout:
                    logger.debug(f"Connection idle timeout, closing: {conn.connection_id}")
                    conn.close()
                    idle_to_remove.append(conn)
                    self._metrics.total_connections_closed += 1
                
                # 检查是否需要验证
                elif idle_time > self.config.idle_timeout / 2 and self.config.test_while_idle:
                    if not self._validate_connection(conn):
                        logger.debug(f"Connection validation failed, closing: {conn.connection_id}")
                        conn.close()
                        idle_to_remove.append(conn)
                        self._metrics.total_connections_closed += 1
                        self._metrics.connection_errors += 1
            
            # 移除无效连接
            for conn in idle_to_remove:
                if conn in self._idle_connections:
                    self._idle_connections.remove(conn)
            
            # 补充最小连接数
            while len(self._idle_connections) + len(self._active_connections) < self.config.pool_min_size:
                try:
                    conn = self._create_connection()
                    self._idle_connections.append(conn)
                    self._metrics.total_connections_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create connection to maintain min size: {e}")
                    break
    
    def _start_reconnect_task(self):
        """启动重连任务"""
        def reconnect_loop():
            while self._running:
                try:
                    self._attempt_reconnect()
                except Exception as e:
                    logger.error(f"Reconnect loop error: {e}")
                
                time.sleep(self.config.retry_delay / 1000)
        
        self._reconnect_task = threading.Thread(target=reconnect_loop, daemon=True)
        self._reconnect_task.start()
    
    def _attempt_reconnect(self):
        """尝试重连"""
        if not self.config.reconnection_enabled:
            return
        
        if not self._running:
            return
        
        # 检查是否需要重连（连接数不足）
        total_connections = len(self._idle_connections) + len(self._active_connections)
        if total_connections >= self.config.pool_min_size:
            return
        
        try:
            logger.info("Attempting to reconnect...")
            self._metrics.reconnect_count += 1
            self._metrics.last_reconnect_time = datetime.now()
            
            # 创建新连接
            conn = self._create_connection()
            self._idle_connections.append(conn)
            self._metrics.total_connections_created += 1
            
            logger.info(f"Reconnected successfully")
            
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            self._metrics.connection_errors += 1
    
    def close(self):
        """关闭连接池"""
        logger.info("Closing connection pool...")
        self._running = False
        
        # 关闭所有连接
        with self._lock:
            for conn in self._idle_connections:
                conn.close()
            self._idle_connections.clear()
            
            for conn in self._active_connections.values():
                conn.close()
            self._active_connections.clear()
        
        logger.info("Connection pool closed")
    
    def get_metrics(self) -> PoolMetrics:
        """获取连接池指标"""
        return self._metrics
    
    def is_healthy(self) -> bool:
        """
        检查连接池是否健康
        
        :return: 是否健康
        """
        with self._lock:
            # 检查最小连接数
            total_connections = len(self._idle_connections) + len(self._active_connections)
            if total_connections < self.config.pool_min_size:
                return False
            
            # 检查熔断器
            if self._circuit_breaker_state == "open":
                return False
            
            return True
    
    def reset_circuit_breaker(self):
        """重置熔断器状态"""
        with self._lock:
            self._circuit_breaker_state = "closed"
            self._circuit_breaker_failures = 0
            self._circuit_breaker_successes = 0
            logger.info("Circuit breaker reset")

    def update_config(self, new_config: PoolConfig):
        """
        热更新连接池配置（不重启池）

        只允许更新运行时可变更的参数：
        - pool_min_size / pool_max_size
        - idle_timeout / connection_timeout
        - health_check_enabled / test_on_borrow / test_on_return / test_while_idle
        - circuit_breaker_* 配置

        不允许热更新的字段需要通过 create_pool() 新建池。

        :param new_config: 新的配置
        """
        with self._lock:
            old_config = self.config
            # 更新允许热更新的字段
            self.config.pool_min_size = new_config.pool_min_size
            self.config.pool_max_size = new_config.pool_max_size
            self.config.idle_timeout = new_config.idle_timeout
            self.config.connection_timeout = new_config.connection_timeout
            self.config.health_check_enabled = new_config.health_check_enabled
            self.config.test_on_borrow = new_config.test_on_borrow
            self.config.test_on_return = new_config.test_on_return
            self.config.test_while_idle = new_config.test_while_idle
            self.config.circuit_breaker_enabled = new_config.circuit_breaker_enabled
            self.config.circuit_breaker_failure_threshold = new_config.circuit_breaker_failure_threshold
            self.config.circuit_breaker_success_threshold = new_config.circuit_breaker_success_threshold
            self.config.circuit_breaker_half_open_max_calls = new_config.circuit_breaker_half_open_max_calls

            logger.info(
                f"Config hot-updated: pool_size={old_config.pool_min_size}/{old_config.pool_max_size} "
                f"→ {self.config.pool_min_size}/{self.config.pool_max_size}, "
                f"idle_timeout={old_config.idle_timeout} → {self.config.idle_timeout}, "
                f"health_check={old_config.health_check_enabled} → {self.config.health_check_enabled}",
                extra={"pool_id": self.pool_id}
            )

    def get_config(self) -> PoolConfig:
        """获取当前配置快照"""
        with self._lock:
            return PoolConfig(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                username=self.config.username,
                password=self.config.password,
                pool_min_size=self.config.pool_min_size,
                pool_max_size=self.config.pool_max_size,
                idle_timeout=self.config.idle_timeout,
                connection_timeout=self.config.connection_timeout,
                idle_test_interval=self.config.idle_test_interval,
                health_check_enabled=self.config.health_check_enabled,
                test_on_borrow=self.config.test_on_borrow,
                test_on_return=self.config.test_on_return,
                test_while_idle=self.config.test_while_idle,
                validation_query=self.config.validation_query,
                validation_timeout=self.config.validation_timeout,
                reconnection_enabled=self.config.reconnection_enabled,
                max_retries=self.config.max_retries,
                retry_delay=self.config.retry_delay,
                exponential_backoff_enabled=self.config.exponential_backoff_enabled,
                exponential_backoff_initial_interval=self.config.exponential_backoff_initial_interval,
                exponential_backoff_max_interval=self.config.exponential_backoff_max_interval,
                exponential_backoff_coefficient=self.config.exponential_backoff_coefficient,
                exponential_backoff_max_retries=self.config.exponential_backoff_max_retries,
                fast_retry_enabled=self.config.fast_retry_enabled,
                fast_retry_max_attempts=self.config.fast_retry_max_attempts,
                circuit_breaker_enabled=self.config.circuit_breaker_enabled,
                circuit_breaker_failure_threshold=self.config.circuit_breaker_failure_threshold,
                circuit_breaker_success_threshold=self.config.circuit_breaker_success_threshold,
                circuit_breaker_half_open_max_calls=self.config.circuit_breaker_half_open_max_calls,
            )


# 全局连接池管理器
_global_pools: Dict[str, ConnectionPool] = {}
_global_lock = threading.Lock()


def create_pool(config: Optional[PoolConfig] = None, name: str = "default") -> ConnectionPool:
    """
    创建连接池
    
    :param config: 连接池配置，None 则使用默认配置
    :param name: 连接池名称
    :return: 连接池实例
    """
    if config is None:
        config = PoolConfig()
    
    with _global_lock:
        if name in _global_pools:
            return _global_pools[name]
        
        pool = ConnectionPool(config)
        _global_pools[name] = pool
        return pool


def get_pool(name: str = "default") -> Optional[ConnectionPool]:
    """
    获取命名连接池
    
    :param name: 连接池名称
    :return: 连接池实例，不存在则返回 None
    """
    with _global_lock:
        return _global_pools.get(name)


def close_all_pools():
    """关闭所有连接池"""
    with _global_lock:
        for name, pool in list(_global_pools.items()):
            pool.close()
            del _global_pools[name]
        logger.info("All connection pools closed")
