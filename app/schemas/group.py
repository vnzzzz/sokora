"""
グループスキーマ定義
================

ユーザーグループのPydanticスキーマ。
"""

from pydantic import BaseModel
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
    group_id: int

    class Config:
        """設定クラス"""
        from_attributes = True


class GroupList(BaseModel):
    """複数グループ取得用スキーマ"""
    groups: List[Group] 