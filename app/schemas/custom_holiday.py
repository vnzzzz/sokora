"""
カスタム祝日のスキーマ
"""

import datetime
from typing import Optional

from fastapi import Form
from pydantic import BaseModel, ConfigDict


class CustomHolidayBase(BaseModel):
    """カスタム祝日の基本スキーマ"""

    date: Optional[datetime.date] = None
    name: Optional[str] = None


class CustomHolidayCreate(CustomHolidayBase):
    """カスタム祝日の作成スキーマ"""

    date: datetime.date
    name: str

    @classmethod
    async def as_form(
        cls,
        date: datetime.date = Form(...),
        name: str = Form(...),
    ) -> "CustomHolidayCreate":
        """フォームデータからインスタンスを生成"""
        return cls(date=date, name=name)


class CustomHolidayUpdate(CustomHolidayBase):
    """カスタム祝日の更新スキーマ"""

    @classmethod
    async def as_form(
        cls,
        date: Optional[datetime.date] = Form(None),
        name: Optional[str] = Form(None),
    ) -> "CustomHolidayUpdate":
        """フォームデータからインスタンスを生成"""
        return cls(date=date, name=name)


class CustomHolidayInDBBase(CustomHolidayBase):
    """DB内のカスタム祝日スキーマ"""

    id: int
    date: datetime.date
    name: str

    model_config = ConfigDict(from_attributes=True)


class CustomHoliday(CustomHolidayInDBBase):
    """読み取り用スキーマ"""

    pass
