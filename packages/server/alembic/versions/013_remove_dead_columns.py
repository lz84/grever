"""Remove dead columns agent_type and estimated_hours

Revision ID: 013
Revises: 012
Create Date: 2026-06-12 17:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop agent_type from scenario_tasks
    with op.batch_alter_table('scenario_tasks', schema=None) as batch_op:
        batch_op.drop_column('agent_type')
    
    # Drop estimated_hours from scenario_tasks
    with op.batch_alter_table('scenario_tasks', schema=None) as batch_op:
        batch_op.drop_column('estimated_hours')
    
    # Drop agent_type from scenario_projects (if it exists)
    # Use raw SQL since batch_alter_table might not handle optional columns well
    try:
        op.execute('ALTER TABLE scenario_projects DROP COLUMN agent_type')
    except Exception:
        # Column may not exist, ignore
        pass


def downgrade() -> None:
    # Add back agent_type to scenario_projects
    with op.batch_alter_table('scenario_projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_type', sa.TEXT(), nullable=True))
    
    # Add back estimated_hours to scenario_tasks
    with op.batch_alter_table('scenario_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('estimated_hours', sa.FLOAT(), nullable=True))
    
    # Add back agent_type to scenario_tasks
    with op.batch_alter_table('scenario_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_type', sa.TEXT(), nullable=True))
