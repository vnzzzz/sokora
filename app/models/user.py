"""
ユーザーモデル定義
================

ユーザーのSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ..db.session import Base


class User(Base):  # type: ignore
    """システム内の従業員を表すユーザーモデル"""

    __tablename__ = "users"

    user_id = Column(String, primary_key=True, nullable=False, index=True)
    username = Column(String, nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False)
    is_contractor = Column(Boolean, default=False, nullable=False)

    # グループとの関連
    group = relationship("Group", back_populates="users")
    # 勤怠記録との関連
    attendance_records = relationship("Attendance", back_populates="user")
