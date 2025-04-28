"""
社員種別スキーマ定義
================

ユーザーの社員種別のPydanticスキーマ。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class UserTypeBase(BaseModel):
    """社員種別の基本スキーマ"""
    name: str


class UserTypeCreate(UserTypeBase):
    """社員種別作成用スキーマ"""
    pass


class UserTypeUpdate(BaseModel):
    """社員種別更新用スキーマ"""
    name: Optional[str] = None


class UserType(UserTypeBase):
    """社員種別取得用スキーマ"""
    id: int

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` により、ORMオブジェクトなどの属性から
        Pydanticモデルを生成できるようになります (旧 `orm_mode = True`)。
        """
        from_attributes = True


class UserTypeList(BaseModel):
    """複数社員種別取得用スキーマ"""
    user_types: List[UserType] 