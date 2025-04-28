"""
グループスキーマ定義
================

ユーザーグループのPydanticスキーマ。
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class GroupBase(BaseModel):
    """グループの基本スキーマ"""
    name: str


class GroupCreate(GroupBase):
    """グループ作成用スキーマ"""
    pass


class GroupUpdate(BaseModel):
    """グループ更新用スキーマ"""
    name: Optional[str] = None


class Group(GroupBase):
    """グループ取得用スキーマ"""
    id: int

    class Config:
        """Pydanticモデルの設定クラス。

        `from_attributes = True` により、ORMオブジェクトなどの属性から
        Pydanticモデルを生成できるようになります (旧 `orm_mode = True`)。
        """
        from_attributes = True


class GroupList(BaseModel):
    """複数グループ取得用スキーマ"""
    groups: List[Group] 