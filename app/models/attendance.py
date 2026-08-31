"""
勤怠記録モデル定義
===============

ユーザーの勤怠記録を管理するSQLAlchemyモデル。
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class Attendance(Base):  # type: ignore
    """ユーザーの日々の勤怠種別を表す勤怠モデル"""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    note = Column(String, nullable=True)

    user = relationship("User", back_populates="attendance_records")
    location_info = relationship("Location", back_populates="attendances")
