"""
勤怠スキーマ
=========

勤怠データのバリデーションとシリアライゼーションのためのPydanticスキーマ。
"""

from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
from pydantic import BaseModel, field_validator, Field


class AttendanceBase(BaseModel):
    """勤怠データの基本スキーマ"""

    date: date
    location_id: int


class AttendanceCreate(AttendanceBase):
    """新規勤怠記録作成用スキーマ"""

    user_id: str  # ユーザーID

    @field_validator('date', mode='before')
    def validate_date(cls, v: Union[str, date]) -> date:
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("日付形式が無効です。YYYY-MM-DD形式で入力してください。")
        return v

    class Config:
        """Pydanticモデルの設定クラス。

        `json_encoders` でdate型をISO形式文字列に変換するよう指定。
        `from_attributes = True` でORMからの変換を有効化。
        """
        json_encoders = {
            date: lambda v: v.isoformat()
        }
        from_attributes = True


class AttendanceUpdate(BaseModel):
    """勤怠データ更新用スキーマ"""

    location_id: Optional[int] = None

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` でORMからの変換を有効化。
        """
        from_attributes = True


class AttendanceInDBBase(AttendanceBase):
    """データベースIDを持つ勤怠の基本スキーマ"""

    id: int
    user_id: str

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` でORMからの変換を有効化。
        """
        from_attributes = True


class Attendance(AttendanceInDBBase):
    """勤怠データレスポンス用スキーマ"""

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` でORMからの変換を有効化。
        """
        from_attributes = True


class AttendanceList(BaseModel):
    """勤怠記録リスト用スキーマ"""

    records: List[Attendance]

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` でORMからの変換を有効化。
        """
        from_attributes = True


class UserAttendance(BaseModel):
    """ユーザー固有の勤怠データ用スキーマ"""

    user_id: str
    user_name: str
    dates: List[Dict[str, Any]]  # 日付、勤務場所、勤怠IDのリスト

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` でORMからの変換を有効化。
        """
        from_attributes = True
