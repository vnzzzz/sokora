"""
勤務場所スキーマ
============

勤務場所データのバリデーションとシリアライゼーションのためのPydanticスキーマ。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    """勤務場所データの基本スキーマ"""

    name: Optional[str]
    color_code: Optional[str] = None


class LocationCreate(LocationBase):
    """新規勤務場所タイプ作成用スキーマ"""

    pass


class LocationUpdate(LocationBase):
    """勤務場所データ更新用スキーマ"""

    name: Optional[str] = None


class LocationInDBBase(LocationBase):
    """データベースIDを持つ勤務場所の基本スキーマ"""

    id: int

    class Config:
        orm_mode = True


class Location(LocationInDBBase):
    """勤務場所データレスポンス用スキーマ"""

    pass


class LocationList(BaseModel):
    """勤務場所リスト用スキーマ"""

    locations: List[Location]
