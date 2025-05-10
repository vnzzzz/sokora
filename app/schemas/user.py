"""
ユーザースキーマ定義
================

ユーザーのPydanticスキーマ。
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from fastapi import Form  # Form をインポート
from .group import Group
from .user_type import UserType


class UserBase(BaseModel):
    """ユーザーの基本スキーマ"""
    id: str = Field(..., description="ユーザーID (半角英数-_)", pattern=r"^[a-zA-Z0-9_-]+$")
    username: str = Field(..., description="ユーザー名")
    group_id: int | str = Field(..., description="所属グループID")
    user_type_id: int | str = Field(..., description="社員種別ID")

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """ユーザー作成用スキーマ"""
    id: str = Field(..., description="ユーザーID (半角英数-_)")

    @classmethod
    async def as_form(
        cls,
        id: str = Form(...),  # idとして直接受け取る
        username: str = Form(...),
        group_id: str = Form(...),
        user_type_id: str = Form(...),
    ) -> 'UserCreate':  # 戻り値の型アノテーションを追加
        """フォームデータからインスタンスを生成"""
        return cls(
            id=id,  # idとして直接渡す
            username=username,
            group_id=group_id,
            user_type_id=user_type_id
        )


class UserUpdate(BaseModel):
    """ユーザー更新用スキーマ"""
    username: str
    group_id: int
    user_type_id: int

    @classmethod
    async def as_form(
        cls,
        username: str = Form(...),
        group_id: int = Form(...),
        user_type_id: int = Form(...),
    ) -> 'UserUpdate':  # 戻り値の型アノテーションを追加
        """フォームデータからインスタンスを生成"""
        return cls(
            username=username,
            group_id=group_id,
            user_type_id=user_type_id
        )


class User(UserBase):
    """ユーザー取得用スキーマ"""
    # user_id: str
    id: str
    group: Optional[Group] = None
    user_type: Optional[UserType] = None

    model_config = ConfigDict(
        from_attributes=True
    )


class UserList(BaseModel):
    """複数ユーザー取得用スキーマ"""
    users: List[User]
