"""add shared auth config table

Revision ID: 9d4f2a7c1b6e
Revises: 4a9c1d2e3f04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9d4f2a7c1b6e"
down_revision: Union[str, None] = "4a9c1d2e3f04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the singleton OIDC configuration table without touching app data."""
    op.create_table(
        "auth_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oidc_enabled", sa.Boolean(), nullable=False),
        sa.Column("oidc_issuer", sa.String(), nullable=True),
        sa.Column("oidc_client_id", sa.String(), nullable=True),
        sa.Column("oidc_client_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("oidc_scope", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop only the shared authentication configuration table."""
    op.drop_table("auth_config")
