"""
そこらスキーマモジュール
=================

このモジュールには、バリデーションとシリアライゼーションのためのPydanticデータスキーマが含まれています。
"""

from .user import User, UserCreate, UserUpdate, UserList
from .attendance import (
    Attendance,
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceList,
    UserAttendance,
)
from .location import Location, LocationCreate, LocationUpdate, LocationList
from .group import Group, GroupCreate, GroupUpdate, GroupList
from .custom_holiday import CustomHoliday, CustomHolidayCreate, CustomHolidayUpdate

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "UserList",
    "Attendance",
    "AttendanceCreate",
    "AttendanceUpdate",
    "AttendanceList",
    "UserAttendance",
    "Location",
    "LocationCreate",
    "LocationUpdate",
    "LocationList",
    "Group",
    "GroupCreate",
    "GroupUpdate",
    "GroupList",
    "CustomHoliday",
    "CustomHolidayCreate",
    "CustomHolidayUpdate",
]
