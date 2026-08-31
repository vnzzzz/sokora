"""Establish Alembic schema baseline.

Revision ID: 2f6c8d1e9a4b
Revises: 6b8f3dbe1e1a
Create Date: 2026-08-30 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "2f6c8d1e9a4b"
down_revision: Union[str, None] = "6b8f3dbe1e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_custom_holiday_server_defaults() -> None:
    """Normalize the pre-#54 create_all schema to the legacy Alembic head."""
    columns = {
        column["name"]: column
        for column in inspect(op.get_bind()).get_columns("custom_holidays")
    }
    missing_defaults = [
        column_name
        for column_name in ("created_at", "updated_at")
        if columns[column_name].get("default") is None
    ]
    if not missing_defaults:
        return

    # The historical Alembic revision created these columns with DB-side
    # CURRENT_TIMESTAMP defaults, while Base.metadata.create_all() only had
    # Python-side defaults. Batch mode lets SQLite converge the adopted schema
    # without rewriting the immutable historical revision.
    with op.batch_alter_table("custom_holidays") as batch_op:
        for column_name in missing_defaults:
            batch_op.alter_column(
                column_name,
                existing_type=sa.DateTime(),
                existing_nullable=False,
                server_default=sa.func.now(),
            )


def upgrade() -> None:
    """Create or normalize the current schema at the Alembic baseline.

    Existing databases reach this revision through the legacy migration chain,
    or are adopted at its head by ``env.py``. Adopted ``create_all`` databases
    are normalized here when their schema differs from the historical Alembic
    head.
    """
    bind = op.get_bind()
    application_tables = set(inspect(bind).get_table_names()) - {"alembic_version"}
    if application_tables:
        _ensure_custom_holiday_server_defaults()
        return

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_groups_id", "groups", ["id"], unique=False)
    op.create_index("ix_groups_name", "groups", ["name"], unique=False)

    op.create_table(
        "user_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_user_types_id", "user_types", ["id"], unique=False)
    op.create_index("ix_user_types_name", "user_types", ["name"], unique=False)

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_locations_id", "locations", ["id"], unique=False)
    op.create_index("ix_locations_name", "locations", ["name"], unique=False)
    op.create_index("ix_locations_category", "locations", ["category"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_type_id"], ["user_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attendance_id", "attendance", ["id"], unique=False)
    op.create_index("ix_attendance_date", "attendance", ["date"], unique=False)

    op.create_table(
        "custom_holidays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", name="uq_custom_holidays_date"),
    )
    op.create_index(
        "ix_custom_holidays_id", "custom_holidays", ["id"], unique=False
    )
    op.create_index(
        "ix_custom_holidays_date", "custom_holidays", ["date"], unique=False
    )


def downgrade() -> None:
    """Keep the legacy-head schema when removing the baseline marker.

    The previous revision already represents this same schema for existing
    databases, so dropping application tables here would make that revision
    invalid.
    """
    pass
