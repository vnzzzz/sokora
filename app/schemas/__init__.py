"""
そこらスキーマモジュール
=================

このモジュールには、バリデーションとシリアライゼーションのためのPydanticデータスキーマが含まれています。
"""

from .attendance import (
    Attendance,
    AttendanceCreate,
    AttendanceList,
    AttendanceUpdate,
    UserAttendance,
)
from .custom_holiday import CustomHoliday, CustomHolidayCreate, CustomHolidayUpdate
from .group import Group, GroupCreate, GroupList, GroupUpdate
from .location import Location, LocationCreate, LocationList, LocationUpdate
from .user import User, UserCreate, UserList, UserUpdate
from .user_type import UserType, UserTypeCreate, UserTypeList, UserTypeUpdate

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
    "UserType",
    "UserTypeCreate",
    "UserTypeUpdate",
    "UserTypeList",
    "CustomHoliday",
    "CustomHolidayCreate",
    "CustomHolidayUpdate",
]
