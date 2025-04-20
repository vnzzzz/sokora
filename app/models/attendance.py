"""
勤怠記録モデル定義
===============

ユーザーの勤怠記録を管理するSQLAlchemyモデル。
"""

from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class Attendance(Base):
    """ユーザーの日々の勤務場所を表す勤怠モデル"""

    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    location = Column(String, nullable=False)

    # ユーザーとの関連付け
    user = relationship("User", back_populates="attendance_records")

    class Config:
        # ユーザーIDと日付の組み合わせに対する一意制約
        unique_together = ("user_id", "date")
