"""Drop estimated_hours from scenario_tasks

Revision ID: 019
Revises: 018
Create Date: 2026-06-12 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '019'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop estimated_hours from scenario_tasks
    with op.batch_alter_table('scenario_tasks', schema=None) as batch_op:
        batch_op.drop_column('estimated_hours')


def downgrade() -> None:
    # Add back estimated_hours to scenario_tasks
    with op.batch_alter_table('scenario_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('estimated_hours', sa.FLOAT(), nullable=True))
