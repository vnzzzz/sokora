"""add user username unique constraint

Revision ID: 4a9c1d2e3f04
Revises: 7c4a1b2d3e5f
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "4a9c1d2e3f04"
down_revision: Union[str, None] = "7c4a1b2d3e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = "uq_users_username"


def _assert_no_duplicates() -> None:
    """UNIQUE追加前に既存username重複が無いことを確認します。"""
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                """
            SELECT username, COUNT(*) AS duplicate_count
            FROM users
            GROUP BY username
            HAVING COUNT(*) > 1
            LIMIT 1
            """
            )
        )
        .first()
    )
    if duplicate is not None:
        # どのidentityを残すかはdomain判断が必要なため、migrationでは自動修正しない。
        raise RuntimeError(
            "users contains duplicate username rows; "
            "resolve duplicates before applying revision 4a9c1d2e3f04"
        )


def _username_unique_exists() -> bool:
    """username単列のUNIQUEが既にあればtrueを返します。"""
    constraints = inspect(op.get_bind()).get_unique_constraints("users")
    return any(
        set(constraint.get("column_names") or []) == {"username"}
        for constraint in constraints
    )


def _named_constraint_exists() -> bool:
    """このrevisionが管理する名前付きUNIQUEが存在するか確認します。"""
    constraints = inspect(op.get_bind()).get_unique_constraints("users")
    return any(
        constraint.get("name") == _CONSTRAINT_NAME
        for constraint in constraints
    )


def upgrade() -> None:
    """既存重複を拒否した上でusers.usernameへUNIQUE制約を追加します。"""
    _assert_no_duplicates()
    if _username_unique_exists():
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_unique_constraint(_CONSTRAINT_NAME, ["username"])


def downgrade() -> None:
    """このrevisionが追加したusers.usernameのUNIQUE制約を削除します。"""
    if not _named_constraint_exists():
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")
