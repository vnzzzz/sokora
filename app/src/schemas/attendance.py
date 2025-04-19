"""
Attendance schemas
================

Pydantic schemas for attendance data validation and serialization.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class AttendanceBase(BaseModel):
    """Base schema for attendance data"""

    date: date
    location: str


class AttendanceCreate(AttendanceBase):
    """Schema for creating a new attendance record"""

    user_id: int  # Database user ID


class AttendanceUpdate(BaseModel):
    """Schema for updating attendance data"""

    location: Optional[str] = None


class AttendanceInDBBase(AttendanceBase):
    """Base schema for attendance with DB ID"""

    id: int
    user_id: int

    class Config:
        orm_mode = True


class Attendance(AttendanceInDBBase):
    """Schema for attendance data response"""

    pass


class AttendanceList(BaseModel):
    """Schema for list of attendance records"""

    records: List[Attendance]


class UserAttendance(BaseModel):
    """Schema for user-specific attendance data"""

    user_id: str
    user_name: str
    dates: List[Dict[str, Any]]  # List of date/location pairs
