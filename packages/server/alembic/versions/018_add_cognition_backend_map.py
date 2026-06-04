"""add_cognition_backend_map

Revision ID: 018
Revises: 017
Create Date: 2026-05-28

Phase 1a: GrASP 门面层与适配层迁移
- Create cognitions table (if not exists)
- Create cognition_backend_map table (cognition_id FK -> cognitions.id ON DELETE CASCADE)

TODO (Phase 1b): cognition_backend_map backend_name, content_hash, created_at
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "018"
down_revision: Union[str, Sequence[str], None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: Create cognitions table (if not exists) ──
    table_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cognitions'"
    )).scalar()
    if table_exists == 0:
        op.create_table(
            'cognitions',
            sa.Column('id', sa.String(64), primary_key=True),
            sa.Column('content', sa.Text, nullable=False),
            sa.Column('domain', sa.String(64), nullable=True),
            sa.Column('type', sa.String(32), nullable=True),
            sa.Column('tags', sa.Text, nullable=True),
            sa.Column('metadata', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        )

    # ── Step 2: Create cognition_backend_map table ──
    map_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cognition_backend_map'"
    )).scalar()
    if map_exists == 0:
        op.create_table(
            'cognition_backend_map',
            sa.Column('cognition_id', sa.String(64), primary_key=True),
            sa.Column('backend_name', sa.String(32), nullable=False),
            sa.Column('content_hash', sa.String(16), nullable=True),
            sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
            sa.ForeignKeyConstraint(
                ['cognition_id'],
                ['cognitions.id'],
                ondelete='CASCADE',
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop cognition_backend_map
    map_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cognition_backend_map'"
    )).scalar()
    if map_exists:
        op.drop_table('cognition_backend_map')

    # Drop cognitions (will fail if FK still exists in some DBs, OK for dev)
    table_exists = conn.execute(sa.text(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cognitions'"
    )).scalar()
    if table_exists:
        op.drop_table('cognitions')