"""
数据库连接池配置
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class PoolConfig:
    """
    连接池配置
    
    参数:
        host: 数据库主机地址
        port: 数据库端口
        database: 数据库名称
        username: 用户名
        password: 密码
        pool_min_size: 最小空闲连接数
        pool_max_size: 最大连接数
        idle_timeout: 空闲超时（毫秒）
        connection_timeout: 连接超时（毫秒）
        idle_test_interval: 空闲连接检查间隔（毫秒）
    """
    # 连接信息
    host: str = "localhost"
    port: int = 5432
    database: str = "nexus"
    username: str = "nexus"
    password: str = "nexus"
    
    # 连接池配置
    pool_min_size: int = 5
    pool_max_size: int = 50
    
    # 超时配置（毫秒）
    idle_timeout: int = 300000  # 5 分钟
    connection_timeout: int = 30000  # 30 秒
    idle_test_interval: int = 60000  # 1 分钟
    
    # 健康检查配置
    health_check_enabled: bool = True
    test_on_borrow: bool = True
    test_on_return: bool = False
    test_while_idle: bool = True
    validation_query: str = "SELECT 1"
    validation_timeout: int = 5000
    
    # 重连配置
    reconnection_enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 1000
    
    # 指数退避重连
    exponential_backoff_enabled: bool = True
    exponential_backoff_initial_interval: int = 1000
    exponential_backoff_max_interval: int = 60000
    exponential_backoff_coefficient: float = 2.0
    exponential_backoff_max_retries: int = -1  # -1 表示无限重试
    
    # 快速重试
    fast_retry_enabled: bool = True
    fast_retry_max_attempts: int = 2
    
    # 熔断配置
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_success_threshold: int = 3
    circuit_breaker_half_open_max_calls: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': self.password,
            'pool_min_size': self.pool_min_size,
            'pool_max_size': self.pool_max_size,
            'idle_timeout': self.idle_timeout,
            'connection_timeout': self.connection_timeout,
            'idle_test_interval': self.idle_test_interval,
            'health_check_enabled': self.health_check_enabled,
            'test_on_borrow': self.test_on_borrow,
            'test_on_return': self.test_on_return,
            'test_while_idle': self.test_while_idle,
            'validation_query': self.validation_query,
            'validation_timeout': self.validation_timeout,
            'reconnection_enabled': self.reconnection_enabled,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'exponential_backoff_enabled': self.exponential_backoff_enabled,
            'exponential_backoff_initial_interval': self.exponential_backoff_initial_interval,
            'exponential_backoff_max_interval': self.exponential_backoff_max_interval,
            'exponential_backoff_coefficient': self.exponential_backoff_coefficient,
            'exponential_backoff_max_retries': self.exponential_backoff_max_retries,
            'fast_retry_enabled': self.fast_retry_enabled,
            'fast_retry_max_attempts': self.fast_retry_max_attempts,
            'circuit_breaker_enabled': self.circuit_breaker_enabled,
            'circuit_breaker_failure_threshold': self.circuit_breaker_failure_threshold,
            'circuit_breaker_success_threshold': self.circuit_breaker_success_threshold,
            'circuit_breaker_half_open_max_calls': self.circuit_breaker_half_open_max_calls,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PoolConfig':
        """从字典创建配置"""
        return cls(
            host=data.get('host', 'localhost'),
            port=data.get('port', 5432),
            database=data.get('database', 'nexus'),
            username=data.get('username', 'nexus'),
            password=data.get('password', 'nexus'),
            pool_min_size=data.get('pool_min_size', 5),
            pool_max_size=data.get('pool_max_size', 50),
            idle_timeout=data.get('idle_timeout', 300000),
            connection_timeout=data.get('connection_timeout', 30000),
            idle_test_interval=data.get('idle_test_interval', 60000),
            health_check_enabled=data.get('health_check_enabled', True),
            test_on_borrow=data.get('test_on_borrow', True),
            test_on_return=data.get('test_on_return', False),
            test_while_idle=data.get('test_while_idle', True),
            validation_query=data.get('validation_query', 'SELECT 1'),
            validation_timeout=data.get('validation_timeout', 5000),
            reconnection_enabled=data.get('reconnection_enabled', True),
            max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 1000),
            exponential_backoff_enabled=data.get('exponential_backoff_enabled', True),
            exponential_backoff_initial_interval=data.get('exponential_backoff_initial_interval', 1000),
            exponential_backoff_max_interval=data.get('exponential_backoff_max_interval', 60000),
            exponential_backoff_coefficient=data.get('exponential_backoff_coefficient', 2.0),
            exponential_backoff_max_retries=data.get('exponential_backoff_max_retries', -1),
            fast_retry_enabled=data.get('fast_retry_enabled', True),
            fast_retry_max_attempts=data.get('fast_retry_max_attempts', 2),
            circuit_breaker_enabled=data.get('circuit_breaker_enabled', True),
            circuit_breaker_failure_threshold=data.get('circuit_breaker_failure_threshold', 5),
            circuit_breaker_success_threshold=data.get('circuit_breaker_success_threshold', 3),
            circuit_breaker_half_open_max_calls=data.get('circuit_breaker_half_open_max_calls', 3),
        )
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'PoolConfig':
        """从 YAML 内容创建配置"""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
            return cls.from_dict(data)
        except ImportError:
            raise RuntimeError("PyYAML is required to load YAML configuration")
        except Exception as e:
            raise ValueError(f"Failed to parse YAML configuration: {e}")
    
    @classmethod
    def from_env(cls, prefix: str = "DATABASE") -> 'PoolConfig':
        """从环境变量创建配置"""
        import os
        
        def get_env(key: str, default=None):
            return os.environ.get(f"{prefix}_{key}".upper(), default)
        
        def get_env_int(key: str, default=None):
            value = get_env(key)
            if value is not None:
                return int(value)
            return default
        
        return cls(
            host=get_env('HOST', 'localhost'),
            port=get_env_int('PORT', 5432),
            database=get_env('DATABASE', 'nexus'),
            username=get_env('USERNAME', 'nexus'),
            password=get_env('PASSWORD', 'nexus'),
            pool_min_size=get_env_int('POOL_MIN_SIZE', 5),
            pool_max_size=get_env_int('POOL_MAX_SIZE', 50),
            idle_timeout=get_env_int('IDLE_TIMEOUT', 300000),
            connection_timeout=get_env_int('CONNECTION_TIMEOUT', 30000),
            idle_test_interval=get_env_int('IDLE_TEST_INTERVAL', 60000),
        )


# ============================================================
# 统一数据库配置（换数据库只改这里）
# ============================================================
#
# 支持三种数据库：
#   - sqlite:     本地开发，零配置
#   - postgresql: 生产环境推荐
#   - mysql:      可选
#
# 切换方式（任选一种）：
#   1. 修改下面 DB_CONFIG 的默认值
#   2. 或设置环境变量: DB_PROVIDER / DB_HOST / DB_DATABASE 等
# ============================================================

import os as _os
from pathlib import Path as _Path
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import Engine as _Engine
from typing import Optional as _Optional

class DBConfig:
    """数据库连接配置（所有模块通过此类获取连接信息）"""
    
    # ---- 数据库类型 ----
    provider: str = "sqlite"  # "sqlite" | "postgresql" | "mysql"
    
    # ---- SQLite ----
    sqlite_path: str = ""
    
    # ---- PostgreSQL / MySQL ----
    host: str = "localhost"
    port: int = 5432
    database: str = "nexus"
    user: str = "nexus"
    password: str = ""
    
    # ---- 连接池 ----
    pool_size: int = 10
    max_overflow: int = 20
    
    def __init__(self):
        # 环境变量优先级最高
        self.provider = _os.getenv("DB_PROVIDER", self.provider).lower()
        if self.provider == "sqlite":
            # 动态解析项目路径，兼容 Windows/Linux
            project_root = _Path(__file__).resolve().parents[5]  # src/shared/database/ → project root
            default_db_path = project_root / "data" / "reins.db"
            self.sqlite_path = _os.getenv("SQLITE_PATH", str(default_db_path))
        else:
            self.host = _os.getenv("DB_HOST", self.host)
            self.port = int(_os.getenv("DB_PORT", str(self.port)))
            self.database = _os.getenv("DB_DATABASE", self.database)
            self.user = _os.getenv("DB_USER", self.user)
            self.password = _os.getenv("DB_PASSWORD", self.password)
    
    @property
    def url(self) -> str:
        """数据库连接字符串"""
        if self.provider == "sqlite":
            return f"sqlite:///{self.sqlite_path}"
        elif self.provider == "postgresql":
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.provider == "mysql":
            return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"不支持的数据库类型: {self.provider}")
    
    @property
    def connect_args(self) -> dict:
        if self.provider == "sqlite":
            return {"check_same_thread": False}
        return {}


# 全局配置实例（所有模块都引用这个）
DB_CONFIG = DBConfig()

# 确保 SQLite data 目录存在
if DB_CONFIG.provider == "sqlite":
    _Path(DB_CONFIG.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

# ============================================================
# Engine 工厂（单例）
# ============================================================
_engine: _Optional[_Engine] = None


def get_engine() -> _Engine:
    """获取 SQLAlchemy engine（单例，所有模块共用）"""
    global _engine
    if _engine is None:
        _engine = _create_engine(
            DB_CONFIG.url,
            pool_size=DB_CONFIG.pool_size,
            max_overflow=DB_CONFIG.max_overflow,
            echo=False,
            connect_args=DB_CONFIG.connect_args,
        )
    return _engine


def get_db_url() -> str:
    """获取数据库连接字符串"""
    return DB_CONFIG.url


def reset_engine():
    """重置 engine（仅测试用）"""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
