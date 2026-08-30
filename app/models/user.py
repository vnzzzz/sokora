"""
ユーザーモデル定義
================

ユーザーのSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from ..db.session import Base


class User(Base):
    """システム内の従業員を表すユーザーモデル"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, index=True)
    user_id = Column(String, unique=True, nullable=False, index=True)

    # 勤怠記録との関連
    attendance_records = relationship("Attendance", back_populates="user")
