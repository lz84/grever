"""
Nexus Reins 数据库方言适配器
支持 SQLite / PostgreSQL / MySQL 多数据库后端
"""

from typing import Literal

class DialectAdapter:
    """数据库方言适配器"""
    
    @staticmethod
    def get_dialect(provider: Literal["sqlite", "postgres", "mysql"]):
        if provider == "sqlite":
            return SQLiteDialect()
        elif provider == "postgres":
            return PostgresDialect()
        elif provider == "mysql":
            return MySQLDialect()
        else:
            raise ValueError(f"Unsupported database provider: {provider}")

class SQLiteDialect:
    """SQLite 方言适配器"""
    
    @staticmethod
    def wrap_create_table_if_not_exists(sql: str) -> str:
        """SQLite 使用 CREATE TABLE IF NOT EXISTS"""
        return sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
    
    @staticmethod
    def wrap_create_index_if_not_exists(sql: str) -> str:
        """SQLite 使用 CREATE INDEX IF NOT EXISTS"""
        return sql.replace("CREATE INDEX", "CREATE INDEX IF NOT EXISTS")
    
    @staticmethod
    def support_deferrable() -> bool:
        return False
    
    @staticmethod
    def json_type() -> str:
        return "TEXT"  # SQLite 没有 JSON 类型，用 TEXT 存储 JSON
    
    @staticmethod
    def timestamp_default() -> str:
        return "CURRENT_TIMESTAMP"
    
    @staticmethod
    def uuid_type() -> str:
        return "TEXT"

class PostgresDialect:
    """PostgreSQL 方言适配器"""
    
    @staticmethod
    def wrap_create_table_if_not_exists(sql: str) -> str:
        return sql  # PostgreSQL 原生支持 CREATE TABLE IF NOT EXISTS
    
    @staticmethod
    def wrap_create_index_if_not_exists(sql: str) -> str:
        return sql
    
    @staticmethod
    def support_deferrable() -> bool:
        return True
    
    @staticmethod
    def json_type() -> str:
        return "JSONB"  # PostgreSQL JSONB 类型
    
    @staticmethod
    def timestamp_default() -> str:
        return "CURRENT_TIMESTAMP"
    
    @staticmethod
    def uuid_type() -> str:
        return "UUID"

class MySQLDialect:
    """MySQL 方言适配器"""
    
    @staticmethod
    def wrap_create_table_if_not_exists(sql: str) -> str:
        return sql
    
    @staticmethod
    def wrap_create_index_if_not_exists(sql: str) -> str:
        return sql
    
    @staticmethod
    def support_deferrable() -> bool:
        return False
    
    @staticmethod
    def json_type() -> str:
        return "JSON"  # MySQL 5.7+ 支持 JSON 类型
    
    @staticmethod
    def timestamp_default() -> str:
        return "CURRENT_TIMESTAMP"
    
    @staticmethod
    def uuid_type() -> str:
        return "CHAR(36)"  # MySQL 用 CHAR 存储 UUID
