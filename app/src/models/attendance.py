"""
Attendance model definitions
===========================

SQLAlchemy models for attendance records.
"""

from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class Attendance(Base):
    """Attendance model representing daily work locations for users"""

    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    location = Column(String, nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="attendance_records")

    class Config:
        # Make this model have a unique constraint on user_id and date
        unique_together = ("user_id", "date")
