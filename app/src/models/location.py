"""
Location model definitions
========================

SQLAlchemy models for work location types.
"""

from sqlalchemy import Column, String, Integer

from ..db.base_class import Base


class Location(Base):
    """Location model representing work location types"""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    color_code = Column(String, nullable=True)  # Optional color code for UI
