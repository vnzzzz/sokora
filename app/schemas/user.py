"""
ユーザースキーマ定義
================

ユーザーのPydanticスキーマ。
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .group import Group
from .user_type import UserType


class UserBase(BaseModel):
    """ユーザーの基本スキーマ"""
    username: str
    group_id: str | int
    user_type_id: str | int


class UserCreate(UserBase):
    """ユーザー作成用スキーマ"""
    id: str = Field(..., alias="user_id")


class UserUpdate(BaseModel):
    """ユーザー更新用スキーマ"""
    username: str
    group_id: int
    user_type_id: int


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
