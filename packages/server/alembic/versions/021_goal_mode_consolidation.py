"""Goal mode consolidation: engineering/research, diversity, portfolio_size

Revision ID: 021
Revises: 020
Create Date: 2026-06-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "021"
down_revision: Union[str, Sequence[str], None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新增字段
    op.add_column('goals', sa.Column('diversity', sa.String(20), default='best', nullable=True))
    op.add_column('goals', sa.Column('portfolio_size', sa.Integer(), default=3, nullable=True))
    op.add_column('goals', sa.Column('original_mode', sa.String(20), nullable=True))
    
    # 保存原始值
    op.execute("UPDATE goals SET original_mode = mode WHERE mode IN ('normal', 'exploration', 'optimization')")
    
    # 迁移 mode 值
    op.execute("UPDATE goals SET mode = 'engineering' WHERE mode = 'normal'")
    op.execute("UPDATE goals SET mode = 'research' WHERE mode IN ('exploration', 'optimization')")


def downgrade() -> None:
    # 回退 mode 值（从 original_mode 恢复）
    op.execute("UPDATE goals SET mode = original_mode WHERE original_mode IN ('normal', 'exploration', 'optimization')")
    op.drop_column('goals', 'original_mode')
    op.drop_column('goals', 'portfolio_size')
    op.drop_column('goals', 'diversity')
