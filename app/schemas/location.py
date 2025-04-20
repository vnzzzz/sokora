"""
勤務場所のスキーマを定義するモジュール
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class LocationBase(BaseModel):
    """勤務場所の基本スキーマ"""
    name: Optional[str] = None


class LocationCreate(LocationBase):
    """勤務場所の作成スキーマ"""
    name: str


class LocationUpdate(LocationBase):
    """勤務場所の更新スキーマ"""
    pass


class LocationInDBBase(LocationBase):
    """データベース内の勤務場所スキーマ"""
    location_id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class Location(LocationInDBBase):
    """勤務場所読み取り用スキーマ"""
    pass


class LocationList(BaseModel):
    """勤務場所一覧スキーマ"""
    locations: List[Location]
