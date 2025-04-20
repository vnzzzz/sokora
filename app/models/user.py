"""
User model definitions
=====================

SQLAlchemy models for users.
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from ..db.base_class import Base


class User(Base):
    """User model representing employees in the system"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, index=True)
    user_id = Column(String, unique=True, nullable=False, index=True)

    # Relationship to attendance records
    attendance_records = relationship("Attendance", back_populates="user")
