"""
ユーザースキーマ定義
================

ユーザーのPydanticスキーマ。
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .group import Group


class UserBase(BaseModel):
    """ユーザーの基本スキーマ"""
    username: str
    group_id: int
    is_contractor: bool = False


class UserCreate(UserBase):
    """ユーザー作成用スキーマ"""
    user_id: str


class UserUpdate(BaseModel):
    """ユーザー更新用スキーマ"""
    username: Optional[str] = None
    group_id: int
    is_contractor: Optional[bool] = None


class User(UserBase):
    """ユーザー取得用スキーマ"""
    user_id: str
    group: Optional[Group] = None

    class Config:
        """設定クラス"""
        from_attributes = True


class UserList(BaseModel):
    """複数ユーザー取得用スキーマ"""
    users: List[User]
