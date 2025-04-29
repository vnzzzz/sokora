"""
グループスキーマ定義
================

ユーザーグループのPydanticスキーマ。
"""

from pydantic import BaseModel, Field, ConfigDict
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

    model_config = ConfigDict(
        from_attributes=True
    )


class GroupList(BaseModel):
    """複数グループ取得用スキーマ"""
    groups: List[Group] 