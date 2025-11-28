"""Add custom_holidays table

Revision ID: 6b8f3dbe1e1a
Revises: bdbed9dbd6c9
Create Date: 2025-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b8f3dbe1e1a'
down_revision: Union[str, None] = 'bdbed9dbd6c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'custom_holidays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', name='uq_custom_holidays_date')
    )
    op.create_index(op.f('ix_custom_holidays_date'), 'custom_holidays', ['date'], unique=False)
    op.create_index(op.f('ix_custom_holidays_id'), 'custom_holidays', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_custom_holidays_id'), table_name='custom_holidays')
    op.drop_index(op.f('ix_custom_holidays_date'), table_name='custom_holidays')
    op.drop_table('custom_holidays')
