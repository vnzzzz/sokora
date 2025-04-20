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
    location: str


class AttendanceCreate(AttendanceBase):
    """新規勤怠記録作成用スキーマ"""

    user_id: int  # データベースユーザーID

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
