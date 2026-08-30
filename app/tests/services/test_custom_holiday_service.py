"""
custom_holiday_service のテスト
"""

import datetime

import pytest
from fastapi import HTTPException

from app.models.custom_holiday import CustomHoliday
from app.schemas.custom_holiday import CustomHolidayCreate, CustomHolidayUpdate
from app.services import custom_holiday_service


def test_create_custom_holiday(db) -> None:
    """祝日を新規作成できる"""
    holiday_in = CustomHolidayCreate(date=datetime.date(2024, 12, 31), name="テスト休")

    created = custom_holiday_service.create_custom_holiday_with_validation(db, custom_holiday_in=holiday_in)

    assert created.id is not None
    assert created.date == holiday_in.date
    assert created.name == "テスト休"


def test_create_custom_holiday_duplicate_date(db) -> None:
    """同じ日付で重複作成はエラー"""
    holiday_in = CustomHolidayCreate(date=datetime.date(2024, 12, 31), name="テスト休")
    custom_holiday_service.create_custom_holiday_with_validation(db, custom_holiday_in=holiday_in)

    with pytest.raises(HTTPException):
        custom_holiday_service.create_custom_holiday_with_validation(
            db,
            custom_holiday_in=CustomHolidayCreate(date=datetime.date(2024, 12, 31), name="別の名前"),
        )


def test_update_custom_holiday(db) -> None:
    """祝日名を更新できる"""
    created = custom_holiday_service.create_custom_holiday_with_validation(
        db, custom_holiday_in=CustomHolidayCreate(date=datetime.date(2024, 12, 31), name="旧名称")
    )

    updated = custom_holiday_service.update_custom_holiday_with_validation(
        db,
        custom_holiday_id=created.id,
        custom_holiday_in=CustomHolidayUpdate(name="新名称"),
    )

    assert updated.name == "新名称"


def test_delete_custom_holiday(db) -> None:
    """祝日を削除できる"""
    created = custom_holiday_service.create_custom_holiday_with_validation(
        db, custom_holiday_in=CustomHolidayCreate(date=datetime.date(2024, 12, 31), name="削除対象")
    )

    deleted = custom_holiday_service.delete_custom_holiday(db, custom_holiday_id=created.id)

    assert deleted.id == created.id
    assert db.query(CustomHoliday).count() == 0
