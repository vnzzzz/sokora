"""
勤怠種別のスキーマを定義するモジュール
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from fastapi import Form


class LocationBase(BaseModel):
    """勤怠種別の基本スキーマ"""
    name: Optional[str] = None


class LocationCreate(LocationBase):
    """勤怠種別の作成スキーマ"""
    name: str

    @classmethod
    async def as_form(
        cls,
        name: str = Form(...),
    ) -> 'LocationCreate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name)


class LocationUpdate(LocationBase):
    """勤怠種別の更新スキーマ"""
    pass

    @classmethod
    async def as_form(
        cls,
        name: Optional[str] = Form(None),
    ) -> 'LocationUpdate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name)


class LocationInDBBase(LocationBase):
    """データベース内の勤怠種別スキーマ"""
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True # ORMオブジェクトからの変換を有効化
    )


class Location(LocationInDBBase):
    """APIレスポンスなどで使用する勤怠種別読み取り用スキーマ。"""
    pass


class LocationList(BaseModel):
    """勤怠種別一覧スキーマ"""
    locations: List[Location]
