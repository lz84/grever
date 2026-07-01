"""Add category, description, output_schema fields to prompt_library table

Revision ID: 020
Revises: 017
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '020'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to prompt_library table
    op.add_column('prompt_library', sa.Column('category', sa.Text, nullable=True))
    op.add_column('prompt_library', sa.Column('description', sa.Text, nullable=True))
    op.add_column('prompt_library', sa.Column('output_schema', sa.Text, nullable=True))


def downgrade() -> None:
    # Remove new columns from prompt_library table
    op.drop_column('prompt_library', 'output_schema')
    op.drop_column('prompt_library', 'description')
    op.drop_column('prompt_library', 'category')
