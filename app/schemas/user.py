"""
ユーザースキーマ
============

ユーザーデータのバリデーションとシリアライゼーションのためのPydanticスキーマ。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """ユーザーデータの基本スキーマ"""

    username: Optional[str]
    user_id: Optional[str]


class UserCreate(UserBase):
    """新規ユーザー作成用スキーマ"""

    pass


class UserUpdate(UserBase):
    """ユーザーデータ更新用スキーマ"""

    username: Optional[str] = None
    user_id: Optional[str] = None


class UserInDBBase(UserBase):
    """データベースIDを持つユーザーの基本スキーマ"""

    id: int

    class Config:
        orm_mode = True


class User(UserInDBBase):
    """ユーザーデータレスポンス用スキーマ"""

    pass


class UserList(BaseModel):
    """ユーザーリスト用スキーマ"""

    users: List[User]
