"""
社員種別スキーマ定義
================

ユーザーの社員種別のPydanticスキーマ。
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from fastapi import Form


class UserTypeBase(BaseModel):
    """社員種別の基本スキーマ"""
    name: str


class UserTypeCreate(UserTypeBase):
    """社員種別作成用スキーマ"""
    order: Optional[int] = None

    @classmethod
    async def as_form(
        cls,
        name: str = Form(...),
        order: Optional[int] = Form(None),
    ) -> 'UserTypeCreate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name, order=order)


class UserTypeUpdate(BaseModel):
    """社員種別更新用スキーマ"""
    name: Optional[str] = None
    order: Optional[int] = None

    @classmethod
    async def as_form(
        cls,
        name: Optional[str] = Form(None),
        order: Optional[int] = Form(None),
    ) -> 'UserTypeUpdate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name, order=order)


class UserType(UserTypeBase):
    """社員種別取得用スキーマ"""
    id: int
    order: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True
    )


class UserTypeList(BaseModel):
    """複数社員種別取得用スキーマ"""
    user_types: List[UserType] 