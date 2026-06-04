# Reins Sprint 1 Plan

**Sprint 周期**：2026-04-08 → 2026-04-21（2周）
**Sprint 目标**：Reins MVP API 层可用，Grasp 集成跑通，持久化层就绪
**状态**：📋 Draft

---

## Sprint Goal

> Reins 服务端可被外部调用，任务分解时能调用 Grasp 注入认知上下文，持久化层就绪且可迁移。

---

## Backlog & Tasks

### P0 🔴 核心路径（必须完成）

| Task ID | 标题 | 类型 | 负责 | 估计 | 验收标准 |
|---------|------|------|------|------|----------|
| **MAK-201** | SQLite 持久化层 | development | 扣子 | 4h | 数据重启不丢，支持迁移脚本生成 |
| **MAK-202** | Reins API Server | development | 扣子 | 8h | HTTP 接口可调用，所有 Manager 方法可访问 |
| **MAK-203** | Grasp 集成-任务分解认知 | development | 扣子 | 4h | decompose()调用 Grasp 查询，返回认知上下文 |
| **MAK-204** | 派发认知抽取集成 | development | 扣子 | 4h | 任务派发时调用 Grasp，返回 cognitions |
| **MAK-205** | 验证-API Server 功能 | verification | 刚子 | 2h | 所有接口实际调用验证，有测试截图 |
| **MAK-206** | 验证-Grasp 集成 | verification | 刚子 | 2h | 实际派发任务验证认知抽取结果 |
| **MAK-207** | 验证-SQlite 持久化 | verification | 刚子 | 2h | 重启服务后数据完整，迁移脚本可执行 |

### P1 🟡 重要功能（应完成）

| Task ID | 标题 | 类型 | 负责 | 估计 | 验收标准 |
|---------|------|------|------|------|----------|
| **MAK-208** | Reins Skill 开发 | development | 扣子 | 6h | Agent 可通过 Skill 接口调用 Reins |
| **MAK-209** | 验证-Reins Skill | verification | 刚子 | 2h | Agent 成功调用 Reins 并完成任务派发 |
| **MAK-210** | 持久化迁移框架设计 | design | 刚子 | 2h | 输出迁移接口文档，支持 PG/MySQL 迁移 |

### P2 🟢 优化（尽量完成）

| Task ID | 标题 | 类型 | 负责 | 估计 | 验收标准 |
|---------|------|------|------|------|----------|
| **MAK-211** | 任务派发后跟踪机制 | development | 扣子 | 4h | 任务状态变更可回调通知 |
| **MAK-212** | Agent 心跳保活集成 | development | 扣子 | 2h | AgentRegistry 与实际心跳联动 |

---

## Sprint Board

```
To Do                    In Progress              Done
─────────────────────────────────────────────────────────────
MAK-201 (扣子)           -                        -
MAK-202 (扣子)           -                        -
MAK-203 (扣子)           -                        -
MAK-204 (扣子)           -                        -
MAK-208 (扣子)           -                        -
MAK-210 (刚子)           -                        -
MAK-211 (扣子)           -                        -
MAK-212 (扣子)           -                        -
                          MAK-205 (刚子)           -
                          MAK-206 (刚子)           -
                          MAK-207 (刚子)           -
                          MAK-209 (刚子)           -
```

---

## SQLite 持久化设计原则

### 迁移友好的 ORM 封装

```python
# reins/persistence/base.py
# 所有 Model 必须继承 BaseModel，支持任意数据库后端

class BaseModel:
    """可迁移的数据模型基类"""
    
    @classmethod
    def to_dict(cls) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> Self: ...
    
    @classmethod
    def create_table_sql(cls) -> str: ...
    @classmethod
    def table_name(cls) -> str: ...

# 使用 SQLAlchemy Core（而非 ORM），天然支持多数据库后端
from sqlalchemy import Table, Column, String, Float, JSON, MetaData

class TaskModel(BaseModel):
    @classmethod
    def create_table_sql(cls) -> str:
        return """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            project_id TEXT,
            goal_id TEXT,
            assigned_agent TEXT,
            status TEXT NOT NULL DEFAULT 'todo',
            priority INTEGER NOT NULL DEFAULT 1,
            dependencies TEXT,  -- JSON array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            estimated_hours REAL,
            actual_hours REAL,
            result TEXT
        );
        """
```

### 迁移脚本规范

```python
# migrations/001_create_tasks.py
"""
迁移: 创建 tasks 表
目标数据库: SQLite (开发) → PostgreSQL (生产)
"""

UP_SQL = """
CREATE TABLE IF NOT EXISTS tasks (...);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
"""

DOWN_SQL = """
DROP INDEX IF EXISTS idx_tasks_project;
DROP INDEX IF NOT EXISTS idx_tasks_status;
DROP TABLE IF EXISTS tasks;
"""

def up(db_engine):
    with db_engine.connect() as conn:
        conn.execute(text(UP_SQL))
        conn.commit()

def down(db_engine):
    with db_engine.connect() as conn:
        conn.execute(text(DOWN_SQL))
        conn.commit()
```

### 数据库配置

```python
# reins/config.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class DatabaseConfig:
    provider: Literal["sqlite", "postgres", "mysql"] = "sqlite"
    path: str = "data/reins.db"  # SQLite 专用
    # PG/MySQL 专用
    host: str = None
    port: int = None
    database: str = None
    user: str = None
    password: str = None

    @property
    def connection_string(self) -> str:
        if self.provider == "sqlite":
            return f"sqlite:///{self.path}"
        elif self.provider == "postgres":
            return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        ...
```

---

## 每日站会时间

**时间**：每天 09:30
**地点**：飞书群

### 报告格式
```
[@所有人] Reins Sprint 1 日报 - YYYY-MM-DD

昨天完成：
- [完成任务]

今天计划：
- [计划任务]

阻塞：
- [阻塞问题，如有]
```

---

## Definition of Done

- [ ] 代码已合并到 main
- [ ] 单元测试通过（pytest）
- [ ] 实际 API 调用验证通过
- [ ] 文档已更新
- [ ] 验证任务由非开发者执行
