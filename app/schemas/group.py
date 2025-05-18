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
    order: Optional[int] = None

    @classmethod
    async def as_form(
        cls,
        name: str = Form(...),
        order: Optional[int] = Form(None),
    ) -> 'GroupCreate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name, order=order)


class GroupUpdate(BaseModel):
    """グループ更新用スキーマ"""
    name: Optional[str] = None
    order: Optional[int] = None

    @classmethod
    async def as_form(
        cls,
        name: Optional[str] = Form(None),  # Optional なのでデフォルトを None に
        order: Optional[int] = Form(None),
    ) -> 'GroupUpdate':
        """フォームデータからインスタンスを生成"""
        return cls(name=name, order=order)


class Group(GroupBase):
    """グループ取得用スキーマ"""
    id: int
    order: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True
    )


class GroupList(BaseModel):
    """複数グループ取得用スキーマ"""
    groups: List[Group] 