"""
Grever Reins 数据库配置
支持 SQLite / PostgreSQL / MySQL
"""
from pathlib import Path

from dataclasses import dataclass
from typing import Literal, Optional
import os

@dataclass
class DatabaseConfig:
    """
    数据库配置
    支持多数据库后端
    """
    provider: Literal["sqlite", "postgres", "mysql"] = "sqlite"
    
    # SQLite 专用
    path: str = "data/reins.db"
    
    # PostgreSQL / MySQL 专用
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    
    # 连接池配置
    pool_size: int = 10
    max_overflow: int = 20
    
    @property
    def connection_string(self) -> str:
        """生成数据库连接字符串"""
        if self.provider == "sqlite":
            return f"sqlite:///{self.path}"
        elif self.provider == "postgres":
            return (
                f"postgresql://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        elif self.provider == "mysql":
            return (
                f"mysql+pymysql://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        else:
            raise ValueError(f"Unsupported database provider: {self.provider}")
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """从环境变量加载配置"""
        # 正确的 Grever DB 路径
        default_db = str(Path(__file__).resolve().parents[4] / "data" / "reins.db")
        return cls(
            provider=os.getenv("REINS_DB_PROVIDER", "sqlite"),
            path=os.getenv("REINS_DB_PATH", default_db),
            host=os.getenv("REINS_DB_HOST"),
            port=int(os.getenv("REINS_DB_PORT", 5432)) if os.getenv("REINS_DB_PORT") else None,
            database=os.getenv("REINS_DB_NAME"),
            user=os.getenv("REINS_DB_USER"),
            password=os.getenv("REINS_DB_PASSWORD"),
        )
