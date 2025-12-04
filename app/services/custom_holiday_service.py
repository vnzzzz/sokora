"""
カスタム祝日サービス
"""

import datetime
from typing import Optional, cast

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, models
from app.utils.holiday_cache import refresh_holiday_cache


def _validate_name(name: Optional[str]) -> None:
    if not name or not str(name).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="祝日名を入力してください",
        )


def _validate_date_unique(db: Session, *, date: Optional[datetime.date], exclude_id: Optional[int] = None) -> None:
    if date is None:
        return
    existing = crud.custom_holiday.get_by_date(db, date=date)
    if existing and existing.id != exclude_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この日付は既に登録されています",
        )


def create_custom_holiday_with_validation(
    db: Session, *, custom_holiday_in: schemas.custom_holiday.CustomHolidayCreate
) -> models.CustomHoliday:
    _validate_name(custom_holiday_in.name)
    _validate_date_unique(db, date=custom_holiday_in.date)

    created = crud.custom_holiday.create(db, obj_in=custom_holiday_in)
    refresh_holiday_cache(db)
    return created


def update_custom_holiday_with_validation(
    db: Session, *, custom_holiday_id: int, custom_holiday_in: schemas.custom_holiday.CustomHolidayUpdate
) -> models.CustomHoliday:
    db_obj = crud.custom_holiday.get_or_404(db, id=custom_holiday_id)
    new_name_raw = custom_holiday_in.name if custom_holiday_in.name is not None else db_obj.name
    new_name: Optional[str] = new_name_raw if new_name_raw is None else str(new_name_raw)
    new_date_raw = custom_holiday_in.date if custom_holiday_in.date is not None else db_obj.date
    new_date: Optional[datetime.date] = (
        None if new_date_raw is None else cast(datetime.date, new_date_raw)
    )

    _validate_name(new_name)
    _validate_date_unique(db, date=new_date, exclude_id=custom_holiday_id)

    updated = crud.custom_holiday.update(
        db,
        db_obj=db_obj,
        obj_in={"name": new_name, "date": new_date},
    )
    refresh_holiday_cache(db)
    return updated


def delete_custom_holiday(db: Session, *, custom_holiday_id: int) -> models.CustomHoliday:
    crud.custom_holiday.get_or_404(db, id=custom_holiday_id)
    deleted = crud.custom_holiday.remove(db, id=custom_holiday_id)
    refresh_holiday_cache(db)
    return deleted
