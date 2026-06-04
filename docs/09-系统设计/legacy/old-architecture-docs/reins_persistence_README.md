# Reins 持久化模块

## 概述

Reins 持久化模块使用 SQLAlchemy Core 作为 ORM 封装，支持 SQLite / PostgreSQL / MySQL 多数据库后端。

## 文件结构

```
reins/persistence/
├── __init__.py          # 模块导出
├── config.py            # 数据库配置
├── dialects.py          # 数据库方言适配器
├── migrator.py          # 迁移运行器
├── utils.py             # 工具函数
├── tables.py            # 表定义（现有）
├── repository.py        # 仓库实现（现有，已修复）
└── migrations/          # 迁移脚本
    ├── 001_create_tasks.sql
    ├── 001_create_tasks.down.sql
    ├── 002_create_goals.sql
    ├── 002_create_goals.down.sql
    ├── 003_create_projects.sql
    ├── 003_create_projects.down.sql
    ├── 004_create_agents.sql
    ├── 004_create_agents.down.sql
    ├── 005_create_disputes.sql
    ├── 005_create_disputes.down.sql
    ├── 006_schema_migrations.sql
    └── 006_schema_migrations.down.sql
```

## 使用方式

### 1. 配置数据库

```python
from reins.persistence import DatabaseConfig

# SQLite 配置
config = DatabaseConfig(
    provider="sqlite",
    path="data/reins.db"
)

# PostgreSQL 配置
config = DatabaseConfig(
    provider="postgres",
    host="localhost",
    port=5432,
    database="reins",
    user="reins_user",
    password="password"
)
```

### 2. 运行迁移

```python
from sqlalchemy import create_engine
from reins.persistence import ReinsMigrator, DatabaseConfig

config = DatabaseConfig(provider="sqlite", path="data/reins.db")
engine = create_engine(config.connection_string)
migrator = ReinsMigrator(engine, config)

# 应用所有未应用的迁移
result = migrator.migrate_up()
print(f"Applied: {[m.version for m in result.applied]}")

# 回滚最后一步迁移
result = migrator.migrate_down(steps=1)
print(f"Rolled back: {[m.version for m in result.rolled_back]}")

# 查看迁移状态
status = migrator.status()
print(f"Applied: {status['applied']}")
print(f"Pending: {status['pending']}")
```

### 3. 创建新迁移

1. 在 `migrations/` 目录创建 SQL 文件，格式：`NNN_description.sql`
2. 创建对应的回滚文件：`NNN_description.down.sql`
3. 运行迁移：`migrator.migrate_up()`

示例 `007_create_new_table.sql`:

```sql
-- Migration: 007_create_new_table
-- Description: 创建新表
-- Author: kouzi
-- Date: 2026-04-08

-- UP Migration
CREATE TABLE IF NOT EXISTS new_table (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
```

示例 `007_create_new_table.down.sql`:

```sql
-- Migration: 007_create_new_table (DOWN)
-- Rollback: Drop new_table table

DROP TABLE IF EXISTS new_table;
```

## 已支持的表

| 版本 | 表名 | 描述 |
|------|------|------|
| 001 | tasks | 任务管理 |
| 002 | goals | 目标管理 |
| 003 | projects | 项目管理 |
| 004 | agents | Agent 注册 |
| 005 | disputes | 争议管理 |
| 006 | schema_migrations | 版本追踪 |

## 数据库兼容性

- ✅ SQLite (开发环境默认)
- ✅ PostgreSQL (生产环境推荐)
- ✅ MySQL (支持)

## 注意事项

1. 迁移脚本已包含 `IF NOT EXISTS`，无需在 dialect 中重复包装
2. 所有 JSON 数据在 SQLite 中存储为 TEXT 类型
3. 生产环境迁移前必须备份数据库
4. 每次迁移必须独立且可回滚
