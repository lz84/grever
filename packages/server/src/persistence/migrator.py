"""
Nexus Reins 数据库迁移运行器
支持 SQLite / PostgreSQL / MySQL 多数据库迁移
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import hashlib
import json
from loguru import logger
from datetime import datetime

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.engine import Engine

from .config import DatabaseConfig
from .dialects import DialectAdapter

# ========== 数据模型 ==========

@dataclass
class Migration:
    """单次迁移"""
    version: str  # e.g., "001"
    name: str  # e.g., "create_tasks"
    up_sql: str  # 升级 SQL
    down_sql: str  # 回滚 SQL
    checksum: str  # SQL 文件的 MD5，用于校验
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None

@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    applied: List[Migration] = field(default_factory=list)
    rolled_back: List[Migration] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __bool__(self):
        return self.success and len(self.errors) == 0

# ========== Schema Version 追踪表 ==========

SCHEMA_VERSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rolled_back_at TIMESTAMP,
    direction TEXT DEFAULT 'up'
);
"""

# ========== 迁移器接口 ==========

class IMigrator(ABC):
    """迁移器接口"""
    
    @abstractmethod
    def get_applied_migrations(self) -> List[Migration]:
        """获取已应用的迁移"""
        pass
    
    @abstractmethod
    def get_pending_migrations(self) -> List[Migration]:
        """获取待应用的迁移"""
        pass
    
    @abstractmethod
    def apply(self, migration: Migration) -> None:
        """应用单个迁移"""
        pass
    
    @abstractmethod
    def rollback(self, migration: Migration) -> None:
        """回滚单个迁移"""
        pass
    
    @abstractmethod
    def migrate_up(self, target_version: str = None) -> MigrationResult:
        """向前迁移到指定版本（或最新）"""
        pass
    
    @abstractmethod
    def migrate_down(self, steps: int = 1) -> MigrationResult:
        """向后回滚指定步数"""
        pass

# ========== Reins 迁移运行器实现 ==========

class ReinsMigrator(IMigrator):
    """Reins 迁移运行器"""
    
    def __init__(self, engine: Engine, config: DatabaseConfig):
        self.engine = engine
        self.config = config
        self.dialect = DialectAdapter.get_dialect(config.provider)
        self.migrations_dir = Path(__file__).parent / "migrations"
        self._ensure_version_table()
    
    def _ensure_version_table(self):
        """确保 schema_migrations 表存在"""
        # SCHEMA_VERSION_TABLE_SQL 已经包含 IF NOT EXISTS，不需要再次包装
        with self.engine.connect() as conn:
            conn.execute(text(SCHEMA_VERSION_TABLE_SQL))
            conn.commit()
    
    def get_applied_migrations(self) -> List[Migration]:
        """获取已应用的迁移"""
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT version, name, checksum, applied_at, rolled_back_at, direction "
                "FROM schema_migrations WHERE direction='up' ORDER BY version"
            ))
            return [
                Migration(
                    version=r.version,
                    name=r.name,
                    checksum=r.checksum,
                    applied_at=str(r.applied_at) if r.applied_at else None,
                    rolled_back_at=str(r.rolled_back_at) if r.rolled_back_at else None,
                    up_sql="",
                    down_sql=""
                )
                for r in rows
            ]
    
    def get_pending_migrations(self) -> List[Migration]:
        """获取待应用的迁移"""
        applied = {m.version for m in self.get_applied_migrations()}
        all_migrations = self._load_all_migrations()
        return [m for m in all_migrations if m.version not in applied]
    
    def apply(self, migration: Migration) -> None:
        """应用单个迁移"""
        with self.engine.begin() as conn:
            # 执行 UP SQL（迁移脚本已包含 IF NOT EXISTS）
            # SQLAlchemy 不支持批量执行，需要分条执行
            import re
            # 分割 SQL 语句（移除注释）
            sql_lines = []
            for line in migration.up_sql.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    sql_lines.append(line)
            
            # 按分号分割并执行
            statements = re.split(r';\s*', '\n'.join(sql_lines))
            for stmt in statements:
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    conn.execute(text(stmt))
            
            # 记录迁移
            conn.execute(text(
                "INSERT INTO schema_migrations (version, name, checksum, direction) "
                "VALUES (:v, :n, :c, 'up')"
            ), {
                "v": migration.version,
                "n": migration.name,
                "c": migration.checksum
            })
    
    def rollback(self, migration: Migration) -> None:
        """回滚单个迁移"""
        if not migration.down_sql:
            raise ValueError(f"No DOWN SQL for migration {migration.version}")
        
        with self.engine.begin() as conn:
            # 执行 DOWN SQL
            import re
            sql_lines = []
            for line in migration.down_sql.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    sql_lines.append(line)
            
            statements = re.split(r';\s*', '\n'.join(sql_lines))
            for stmt in statements:
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    conn.execute(text(stmt))
            
            # 更新迁移记录
            conn.execute(text(
                "UPDATE schema_migrations "
                "SET rolled_back_at=NOW(), direction='down' "
                "WHERE version=:v"
            ), {"v": migration.version})
    
    def migrate_up(self, target_version: str = None) -> MigrationResult:
        """向前迁移到指定版本（或最新）"""
        pending = self.get_pending_migrations()
        if not pending:
            return MigrationResult(success=True, applied=[], rolled_back=[], errors=[])
        
        # 如果有目标版本，只迁移到该版本
        if target_version:
            pending = [m for m in pending if m.version <= target_version]
        
        applied = []
        errors = []
        
        for migration in pending:
            try:
                self.apply(migration)
                applied.append(migration)
                logger.info(f"Applied migration {migration.version}: {migration.name}")
            except Exception as e:
                error_msg = f"Migration {migration.version} failed: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                break
        
        return MigrationResult(
            success=len(errors) == 0,
            applied=applied,
            rolled_back=[],
            errors=errors
        )
    
    def migrate_down(self, steps: int = 1) -> MigrationResult:
        """向后回滚指定步数"""
        applied = self.get_applied_migrations()
        if not applied:
            return MigrationResult(success=True, applied=[], rolled_back=[], errors=[])
        
        # 获取最近应用的 steps 个迁移
        to_rollback = list(reversed(applied))[:steps]
        rolled_back = []
        errors = []
        
        for migration in to_rollback:
            # 重新加载 DOWN SQL
            migration = self._load_migration_sql(migration.version)
            if not migration.down_sql:
                errors.append(f"No DOWN SQL for migration {migration.version}")
                continue
            
            try:
                self.rollback(migration)
                rolled_back.append(migration)
                logger.info(f"Rolled back migration {migration.version}: {migration.name}")
            except Exception as e:
                error_msg = f"Rollback {migration.version} failed: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                break
        
        return MigrationResult(
            success=len(errors) == 0,
            applied=[],
            rolled_back=rolled_back,
            errors=errors
        )
    
    def migrate_to(self, version: str) -> MigrationResult:
        """迁移到指定版本"""
        applied_versions = {m.version for m in self.get_applied_migrations()}
        
        # 如果需要回滚
        if version in applied_versions:
            # 回滚到目标版本之后
            to_rollback = [m for m in reversed(list(applied_versions)) if m > version]
            result = MigrationResult(success=True, applied=[], rolled_back=[])
            for v in to_rollback:
                migration = self._load_migration_sql(v)
                if migration and migration.down_sql:
                    try:
                        self.rollback(migration)
                        result.rolled_back.append(migration)
                    except Exception as e:
                        result.errors.append(f"Rollback {v} failed: {e}")
                        result.success = False
                        break
            return result
        
        # 向前迁移到目标版本
        result = self.migrate_up(target_version=version)
        return result
    
    def _load_migration_sql(self, version: str) -> Optional[Migration]:
        """从文件加载迁移 SQL"""
        migration_files = list(self.migrations_dir.glob(f"{version}_*.sql"))
        if not migration_files:
            return None
        
        up_file = migration_files[0]
        down_file = up_file.with_name(up_file.stem + ".down.sql")
        
        up_sql = up_file.read_text(encoding="utf-8")
        down_sql = down_file.read_text(encoding="utf-8") if down_file.exists() else ""
        
        checksum = hashlib.md5(up_sql.encode()).hexdigest()
        name = "_".join(up_file.stem.split("_")[1:])
        
        return Migration(
            version=version,
            name=name,
            up_sql=up_sql,
            down_sql=down_sql,
            checksum=checksum
        )
    
    def _load_all_migrations(self) -> List[Migration]:
        """加载所有迁移文件"""
        migrations = []
        for f in sorted(self.migrations_dir.glob("*.sql")):
            if f.name.endswith(".down.sql"):
                continue
            
            up_sql = f.read_text(encoding="utf-8")
            down_f = f.with_name(f.name.replace(".sql", ".down.sql"))
            down_sql = down_f.read_text(encoding="utf-8") if down_f.exists() else ""
            
            checksum = hashlib.md5(up_sql.encode()).hexdigest()
            version = f.stem.split("_")[0]
            name = "_".join(f.stem.split("_")[1:])
            
            migrations.append(Migration(
                version=version,
                name=name,
                up_sql=up_sql,
                down_sql=down_sql,
                checksum=checksum
            ))
        
        return migrations
    
    def status(self) -> dict:
        """获取迁移状态"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            "applied": [m.version for m in applied],
            "pending": [m.version for m in pending],
            "total_applied": len(applied),
            "total_pending": len(pending)
        }
