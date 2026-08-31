"""add attendance user/date unique constraint

Revision ID: 7c4a1b2d3e5f
Revises: 2f6c8d1e9a4b
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c4a1b2d3e5f"
down_revision: Union[str, None] = "2f6c8d1e9a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = "uq_attendance_user_date"


def _assert_no_duplicates() -> None:
    """UNIQUE追加前に既存の(user_id, date)重複が無いことを確認します。"""
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                """
            SELECT user_id, date, COUNT(*) AS duplicate_count
            FROM attendance
            GROUP BY user_id, date
            HAVING COUNT(*) > 1
            LIMIT 1
            """
            )
        )
        .first()
    )
    if duplicate is not None:
        # どの重複行を残すかはdomain判断が必要なため、migrationでは自動dedupeしない。
        raise RuntimeError(
            "attendance contains duplicate (user_id, date) rows; "
            "resolve duplicates before applying revision 7c4a1b2d3e5f"
        )


def upgrade() -> None:
    """既存重複を拒否した上でattendance(user_id, date)へUNIQUE制約を追加します。"""
    _assert_no_duplicates()
    with op.batch_alter_table("attendance") as batch_op:
        batch_op.create_unique_constraint(
            _CONSTRAINT_NAME,
            ["user_id", "date"],
        )


def downgrade() -> None:
    """attendance(user_id, date)のUNIQUE制約を削除します。"""
    with op.batch_alter_table("attendance") as batch_op:
        batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")
