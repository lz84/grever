"""add pack_id to skills

Revision ID: 040
Revises: 016
Create Date: 2026-06-12 01:47:31

Sprint 109: Industry Pack Skill Support
- Add pack_id foreign key to skills table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "040"
down_revision: Union[str, Sequence[str], None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if skills table already has pack_id column
    result = conn.execute(
        sa.text("PRAGMA table_info(skills)")
    ).fetchall()
    column_names = [row[1] for row in result]

    if 'pack_id' not in column_names:
        with op.batch_alter_table('skills', schema=None) as batch_op:
            batch_op.add_column(sa.Column('pack_id', sa.String(36), sa.ForeignKey('industry_packs.id', ondelete='CASCADE'), nullable=False, index=True))


def downgrade() -> None:
    conn = op.get_bind()

    # Check if skills table has pack_id column
    result = conn.execute(
        sa.text("PRAGMA table_info(skills)")
    ).fetchall()
    column_names = [row[1] for row in result]

    if 'pack_id' in column_names:
        with op.batch_alter_table('skills', schema=None) as batch_op:
            batch_op.drop_column('pack_id')
