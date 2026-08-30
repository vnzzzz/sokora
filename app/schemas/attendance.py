"""
勤怠スキーマ
=========

勤怠データのバリデーションとシリアライゼーションのためのPydanticスキーマ。
"""

from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
from pydantic import BaseModel, Field, validator


class AttendanceBase(BaseModel):
    """勤怠データの基本スキーマ"""

    date: date
    location_id: int


class AttendanceCreate(AttendanceBase):
    """新規勤怠記録作成用スキーマ"""

    user_id: str  # ユーザーID

    @validator('date')
    def validate_date(cls, v: Union[str, date]) -> date:
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("日付形式が無効です。YYYY-MM-DD形式で入力してください。")
        return v

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()  # dateオブジェクトをISO形式の文字列に変換
        }
        from_attributes = True  # Pydantic V2の新しい設定


class AttendanceUpdate(BaseModel):
    """勤怠データ更新用スキーマ"""

    location_id: Optional[int] = None

    class Config:
        from_attributes = True


class AttendanceInDBBase(AttendanceBase):
    """データベースIDを持つ勤怠の基本スキーマ"""

    id: int
    user_id: str

    class Config:
        from_attributes = True


class Attendance(AttendanceInDBBase):
    """勤怠データレスポンス用スキーマ"""

    class Config:
        from_attributes = True


class AttendanceList(BaseModel):
    """勤怠記録リスト用スキーマ"""

    records: List[Attendance]

    class Config:
        from_attributes = True


class UserAttendance(BaseModel):
    """ユーザー固有の勤怠データ用スキーマ"""

    user_id: str
    user_name: str
    dates: List[Dict[str, Any]]  # 日付、勤務場所、勤怠IDのリスト

    class Config:
        from_attributes = True
