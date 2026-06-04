"""add_platform_type_and_agents_config

Revision ID: 017
Revises: 016
Create Date: 2026-05-28

Phase 1: DB migration for unified agent registration & dispatch
- Add platform_type column to agents table (VARCHAR(32), DEFAULT 'openclaw')
- Create agents_config table (agent_id PK FK→agents.id, platform_type, config_json, created_at, updated_at)
- Data migration: existing agents' trigger_mode/address/metadata → agents_config (platform_type='openclaw')
"""

from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: Union[str, Sequence[str], None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: Add platform_type column to agents table ──
    # Check if column already exists (idempotent)
    col_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM pragma_table_info('agents') WHERE name='platform_type'"
    )).scalar()
    if col_exists == 0:
        op.add_column(
            'agents',
            sa.Column('platform_type', sa.String(32), nullable=False, server_default='openclaw')
        )

    # ── Step 2: Create agents_config table ──
    # Check if table already exists
    table_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='agents_config'"
    )).scalar()
    if table_exists == 0:
        op.create_table(
            'agents_config',
            sa.Column('agent_id', sa.String(32), primary_key=True),
            sa.Column('platform_type', sa.String(32), nullable=False, server_default='openclaw'),
            sa.Column('config_json', sa.Text, nullable=False, server_default='{}'),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime, nullable=True),
            sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        )

    # ── Step 3: Data migration — populate agents_config for existing agents ──
    # Migrate existing agents' data into agents_config with platform_type='openclaw'
    # Only insert for agents that don't already have a config entry
    existing_rows = conn.execute(sa.text(
        "SELECT id, trigger_mode, address, metadata, model_name "
        "FROM agents WHERE id NOT IN (SELECT agent_id FROM agents_config)"
    )).fetchall()

    now = datetime.now()
    for row in existing_rows:
        # Build config_json from legacy fields
        config = {}
        if row.trigger_mode:
            config['trigger_mode'] = row.trigger_mode
        if row.address:
            config['address'] = row.address
        if row.metadata:
            import json
            try:
                meta = json.loads(row.metadata)
                config.update(meta)
            except (json.JSONDecodeError, TypeError):
                pass
        if row.model_name:
            config['model'] = row.model_name

        import json as _json
        conn.execute(sa.text(
            "INSERT INTO agents_config (agent_id, platform_type, config_json, created_at) "
            "VALUES (:agent_id, 'openclaw', :config_json, :created_at)"
        ), {
            'agent_id': row.id,
            'config_json': _json.dumps(config, ensure_ascii=False),
            'created_at': now,
        })

    if existing_rows:
        conn.commit()


def downgrade() -> None:
    conn = op.get_bind()

    # Drop agents_config table
    table_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='agents_config'"
    )).scalar()
    if table_exists:
        op.drop_table('agents_config')

    # Drop platform_type column from agents (SQLite limitation: recreate table)
    col_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM pragma_table_info('agents') WHERE name='platform_type'"
    )).scalar()
    if col_exists:
        # SQLite doesn't support DROP COLUMN directly in older versions
        # We'll use the ALTER TABLE DROP COLUMN (SQLite 3.35.0+)
        try:
            op.drop_column('agents', 'platform_type')
        except Exception:
            # Fallback: recreate table without the column
            op.execute(sa.text("""
                CREATE TABLE agents_backup AS
                SELECT id, name, capability_tags, status, address, metadata,
                       load, current_tasks, registered_at, last_heartbeat,
                       trigger_mode, poll_interval_seconds, max_concurrent_tasks,
                       load_threshold, recovery_threshold, updated_at, model_name,
                       health_status, last_status_change, consecutive_offline_count,
                       max_offline_before_deactivate
                FROM agents
            """))
            op.execute(sa.text("DROP TABLE agents"))
            op.execute(sa.text("""
                CREATE TABLE agents (
                    id VARCHAR(32) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    capability_tags JSON NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    address VARCHAR(500),
                    metadata JSON,
                    load INTEGER NOT NULL,
                    current_tasks INTEGER NOT NULL,
                    registered_at DATETIME NOT NULL,
                    last_heartbeat DATETIME NOT NULL,
                    trigger_mode VARCHAR(20) NOT NULL DEFAULT 'sse',
                    poll_interval_seconds INTEGER NOT NULL DEFAULT 10,
                    max_concurrent_tasks INTEGER NOT NULL DEFAULT 5,
                    load_threshold INTEGER NOT NULL DEFAULT 80,
                    recovery_threshold INTEGER NOT NULL DEFAULT 50,
                    updated_at DATETIME,
                    model_name VARCHAR(255),
                    health_status VARCHAR(20) DEFAULT 'online',
                    last_status_change DATETIME,
                    consecutive_offline_count INTEGER DEFAULT 0,
                    max_offline_before_deactivate INTEGER DEFAULT 5
                )
            """))
            op.execute(sa.text("""
                INSERT INTO agents
                SELECT * FROM agents_backup
            """))
            op.execute(sa.text("DROP TABLE agents_backup"))
