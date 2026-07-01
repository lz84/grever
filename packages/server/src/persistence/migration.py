"""
Grever Reins 迁移系统
支持 SQLite 到 PostgreSQL 的迁移脚本生成
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Callable
from sqlalchemy import create_engine, text
import re


class Migration(ABC):
    """迁移基类"""
    
    @property
    @abstractmethod
    def migration_id(self) -> str:
        """迁移 ID"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """迁移描述"""
        pass
    
    @abstractmethod
    def up(self, db_engine) -> None:
        """向上迁移"""
        pass
    
    @abstractmethod
    def down(self, db_engine) -> None:
        """向下迁移"""
        pass


class CreateTableMigration(Migration):
    """创建表的迁移"""
    
    def __init__(
        self,
        migration_id: str,
        description: str,
        create_sql: str,
        drop_sql: str,
    ):
        self._migration_id = migration_id
        self._description = description
        self._create_sql = create_sql
        self._drop_sql = drop_sql
    
    @property
    def migration_id(self) -> str:
        return self._migration_id
    
    @property
    def description(self) -> str:
        return self._description
    
    def up(self, db_engine) -> None:
        with db_engine.connect() as conn:
            conn.execute(text(self._create_sql))
            conn.commit()
    
    def down(self, db_engine) -> None:
        with db_engine.connect() as conn:
            conn.execute(text(self._drop_sql))
            conn.commit()


class AddIndexMigration(Migration):
    """添加索引的迁移"""
    
    def __init__(
        self,
        migration_id: str,
        description: str,
        create_sql: str,
        drop_sql: str,
    ):
        self._migration_id = migration_id
        self._description = description
        self._create_sql = create_sql
        self._drop_sql = drop_sql
    
    @property
    def migration_id(self) -> str:
        return self._migration_id
    
    @property
    def description(self) -> str:
        return self._description
    
    def up(self, db_engine) -> None:
        with db_engine.connect() as conn:
            conn.execute(text(self._create_sql))
            conn.commit()
    
    def down(self, db_engine) -> None:
        with db_engine.connect() as conn:
            conn.execute(text(self._drop_sql))
            conn.commit()


class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, db_engine, migrations: List[Migration]):
        self._engine = db_engine
        self._migrations = migrations
    
    def _ensure_migrations_table(self):
        """确保迁移记录表存在"""
        with self._engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS __migrations__ (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def _get_applied_migrations(self) -> set:
        """获取已应用的迁移"""
        with self._engine.connect() as conn:
            rows = conn.execute(text("SELECT id FROM __migrations__")).fetchall()
            return {row.id for row in rows}
    
    def migrate(self, to_migration_id: str = None) -> None:
        """
        执行迁移
        
        Args:
            to_migration_id: 迁移到的目标 ID，None 表示迁移到最新
        """
        self._ensure_migrations_table()
        applied = self._get_applied_migrations()
        
        # 按 ID 排序迁移
        sorted_migrations = sorted(self._migrations, key=lambda m: m.migration_id)
        
        if to_migration_id:
            # 迁移到指定版本
            target_index = next(
                (i for i, m in enumerate(sorted_migrations) if m.migration_id == to_migration_id),
                None
            )
            if target_index is None:
                raise ValueError(f"Migration not found: {to_migration_id}")
            
            # 向下迁移到未应用的最大 ID
            while applied:
                max_applied = max(applied)
                max_index = next(i for i, m in enumerate(sorted_migrations) if m.migration_id == max_applied)
                if max_index >= target_index:
                    sorted_migrations[max_index].down(self._engine)
                    applied.remove(max_applied)
                else:
                    break
            
            # 向上迁移到目标
            for migration in sorted_migrations:
                if migration.migration_id in applied:
                    continue
                if migration.migration_id > to_migration_id:
                    break
                migration.up(self._engine)
                with self._engine.connect() as conn:
                    conn.execute(
                        text("INSERT INTO __migrations__ (id, description) VALUES (:id, :desc)"),
                        {"id": migration.migration_id, "desc": migration.description}
                    )
                    conn.commit()
        else:
            # 迁移到最新
            for migration in sorted_migrations:
                if migration.migration_id not in applied:
                    migration.up(self._engine)
                    with self._engine.connect() as conn:
                        conn.execute(
                            text("INSERT INTO __migrations__ (id, description) VALUES (:id, :desc)"),
                            {"id": migration.migration_id, "desc": migration.description}
                        )
                        conn.commit()
    
    def generate_pg_sql(self) -> str:
        """
        生成 PostgreSQL 迁移 SQL 脚本
        将 SQLite 语法转换为 PostgreSQL 语法
        """
        from persistence.tables import metadata
        
        sql_lines = ["-- Reins 迁移脚本 (SQLite -> PostgreSQL)"]
        sql_lines.append("-- 自动生成，请勿手动修改\n")
        
        for table in metadata.sorted_tables:
            # 生成创建表 SQL
            create_sql = str(table.to_sql_compiler())
            
            # 替换 SQLite 特定语法
            create_sql = re.sub(r"INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY", create_sql)
            create_sql = re.sub(r"TEXT", "TEXT", create_sql)
            create_sql = re.sub(r"JSON", "JSONB", create_sql)
            create_sql = re.sub(r"DEFAULT CURRENT_TIMESTAMP", "DEFAULT NOW()", create_sql)
            create_sql = re.sub(r"IF NOT EXISTS", "", create_sql)
            
            sql_lines.append(f"-- Table: {table.name}")
            sql_lines.append(f"CREATE TABLE {table.name} (\n")
            sql_lines.append(f"    {create_sql}\n")
            sql_lines.append(");\n")
            
            # 添加索引
            for index in table.indexes:
                index_sql = str(index.to_sql_compiler())
                index_sql = index_sql.replace("IF NOT EXISTS", "")
                sql_lines.append(f"-- Index: {index.name}")
                sql_lines.append(f"CREATE INDEX {index.name} ON {table.name} {index_sql}\n")
                sql_lines.append("\n")
        
        return "\n".join(sql_lines)
    
    def get_migration_script_path(self, output_path: str = "migrations/reins_migration.sql") -> str:
        """获取迁移脚本路径并生成文件"""
        import os
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        sql_content = self.generate_pg_sql()
        output_file.write_text(sql_content)
        
        return str(output_file)
