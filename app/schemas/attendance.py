"""
勤怠スキーマ
=========

勤怠データのバリデーションとシリアライゼーションのためのPydanticスキーマ。
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class AttendanceBase(BaseModel):
    """勤怠データの基本スキーマ"""

    date: date
    location: str


class AttendanceCreate(AttendanceBase):
    """新規勤怠記録作成用スキーマ"""

    user_id: int  # データベースユーザーID


class AttendanceUpdate(BaseModel):
    """勤怠データ更新用スキーマ"""

    location: Optional[str] = None


class AttendanceInDBBase(AttendanceBase):
    """データベースIDを持つ勤怠の基本スキーマ"""

    id: int
    user_id: int

    class Config:
        orm_mode = True


class Attendance(AttendanceInDBBase):
    """勤怠データレスポンス用スキーマ"""

    pass


class AttendanceList(BaseModel):
    """勤怠記録リスト用スキーマ"""

    records: List[Attendance]


class UserAttendance(BaseModel):
    """ユーザー固有の勤怠データ用スキーマ"""

    user_id: str
    user_name: str
    dates: List[Dict[str, Any]]  # 日付/勤務場所のペアリスト
