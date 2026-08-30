"""
グループスキーマ定義
================

ユーザーグループのPydanticスキーマ。
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from fastapi import Form  # Form をインポート


class GroupBase(BaseModel):
    """グループの基本スキーマ"""
    name: str


class GroupCreate(GroupBase):
    """グループ作成用スキーマ"""
    pass

    @classmethod
    async def as_form(
        cls,
        name: str = Form(...),
    ) -> 'GroupCreate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name)


class GroupUpdate(BaseModel):
    """グループ更新用スキーマ"""
    name: Optional[str] = None

    @classmethod
    async def as_form(
        cls,
        name: Optional[str] = Form(None),  # Optional なのでデフォルトを None に
    ) -> 'GroupUpdate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name)


class Group(GroupBase):
    """グループ取得用スキーマ"""
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )


class GroupList(BaseModel):
    """複数グループ取得用スキーマ"""
    groups: List[Group] 