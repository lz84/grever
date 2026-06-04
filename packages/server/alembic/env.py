"""
Alembic environment configuration for Nexus Reins

Imports all SQLAlchemy models from reins.models so that autogenerate
can detect schema changes.
"""

from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool, MetaData, Table, Column, String
from alembic import context

# ── sys.path setup ──────────────────────────────────────────────────────────
# Ensure packages/server/src is on the path so we can import the models
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ── Alembic Config object ────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Database URL from DB_CONFIG ─────────────────────────────────────────────
from shared.database.config import DB_CONFIG

# Patch the config so engine_from_config picks up the correct URL
config.set_main_option("sqlalchemy.url", DB_CONFIG.url)

# ── Custom metadata for the pre-existing schema_migrations table ───────────
# The existing table has a PK column named "version" (not Alembic's default "version_num").
_custom_version_meta = MetaData()
_custom_version_table = Table(
    "schema_migrations",
    _custom_version_meta,
    Column("version", String(32), primary_key=True),
)

# ── Model metadata ───────────────────────────────────────────────────────────
from models.base import Base as _Base
from models import (  # noqa: F401 – needed to register ORM classes
    Task, Goal, Project, Agent, Workflow, WorkflowStep, Solution,
    IterationConstraint,
)

target_metadata = _Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DBAPI)."""
    context.configure(
        url=DB_CONFIG.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="schema_migrations",
        version_table_column="version_num",
        version_table_metadata=_custom_version_meta,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with Engine + connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="schema_migrations",
            version_table_column="version_num",
            version_table_metadata=_custom_version_meta,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()