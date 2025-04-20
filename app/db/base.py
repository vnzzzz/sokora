"""
Database base imports
====================

Import all models here to ensure they are registered with SQLAlchemy.
"""

from .base_class import Base
from ..models.user import User
from ..models.attendance import Attendance
from ..models.location import Location
