"""
Grever Reins 持久化基础模块
提供 SQLAlchemy Core 封装和数据库配置
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional
from pathlib import Path

@dataclass
class DatabaseConfig:
    """数据库配置"""
    provider: Literal["sqlite", "postgres", "mysql"] = "sqlite"
    # SQLite 专用
    path: str = r"D:\\work\\research\\agents-nexus\\data\\reins.db"
    # PG/MySQL 专用
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    pool_size: int = 20
    max_overflow: int = 40

    @property
    def connection_string(self) -> str:
        """生成连接字符串"""
        if self.provider == "sqlite":
            db_path = Path(self.path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # ⚠️ 防御：如果文件不存在，判断是初始化还是配置错误
            # SQLite 遇到父目录存在但文件不存在时会自动创建空文件，
            # 这在运行时会造成"指向错误 DB"而不报错，是严重隐患。
            if not db_path.exists():
                init_mode = os.getenv("REINS_INIT_MODE", "false").lower() == "true"
                if not init_mode:
                    raise FileNotFoundError(
                        f"[REINS] DB 文件不存在: {db_path.absolute()}。"
                        "如为首次初始化，请设置环境变量 REINS_INIT_MODE=true"
                    )
                # 初始化模式：允许 SQLite 创建文件（create_tables 随后建表）

            return f"sqlite:///{self.path}"
        elif self.provider == "postgres":
            if not all([self.host, self.port, self.database, self.user, self.password]):
                raise ValueError("PostgreSQL 配置不完整")
            return (
                f"postgresql://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        elif self.provider == "mysql":
            if not all([self.host, self.port, self.database, self.user, self.password]):
                raise ValueError("MySQL 配置不完整")
            return (
                f"mysql+pymysql://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        else:
            raise ValueError(f"不支持的数据库类型：{self.provider}")
