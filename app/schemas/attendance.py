"""
勤怠スキーマ
=========

勤怠データのバリデーションとシリアライゼーションのためのPydanticスキーマ。
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator


class AttendanceBase(BaseModel):
    """勤怠データの基本スキーマ"""

    date: date
    location_id: int
    note: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    """新規勤怠記録作成用スキーマ"""

    user_id: str

    @field_validator("date", mode="before")
    def validate_date(cls, v: Union[str, date]) -> date:
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(
                    "日付形式が無効です。YYYY-MM-DD形式で入力してください。"
                )
        return v

    model_config = ConfigDict(from_attributes=True)


class AttendanceUpdate(BaseModel):
    """勤怠データ更新用スキーマ"""

    location_id: Optional[int] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AttendanceInDBBase(AttendanceBase):
    """データベースIDを持つ勤怠の基本スキーマ"""

    id: int
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class Attendance(AttendanceInDBBase):
    """勤怠データレスポンス用スキーマ"""

    model_config = ConfigDict(from_attributes=True)


class AttendanceList(BaseModel):
    """勤怠記録リスト用スキーマ"""

    records: List[Attendance]

    model_config = ConfigDict(from_attributes=True)


class UserAttendance(BaseModel):
    """ユーザー固有の勤怠データ用スキーマ"""

    user_id: str
    user_name: str
    dates: List[Dict[str, Any]]  # 各要素は日付・勤怠種別・勤怠IDを含む。

    model_config = ConfigDict(from_attributes=True)
