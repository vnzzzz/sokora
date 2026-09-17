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
        """form fieldからcreate schemaを構築する。

        Args:
            date: 祝日として登録する日付。
            name: 祝日名。

        Returns:
            form値を保持する`CustomHolidayCreate`。
        """
        return cls(date=date, name=name)


class CustomHolidayUpdate(CustomHolidayBase):
    """カスタム祝日の更新スキーマ"""

    @classmethod
    async def as_form(
        cls,
        date: Optional[datetime.date] = Form(None),
        name: Optional[str] = Form(None),
    ) -> "CustomHolidayUpdate":
        """form fieldからupdate schemaを構築する。

        Args:
            date: optionalな更新後日付。
            name: optionalな更新後祝日名。

        Returns:
            form値を保持する`CustomHolidayUpdate`。
        """
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
