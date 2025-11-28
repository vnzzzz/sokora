"""
カスタム祝日CRUD操作
"""

import datetime
from typing import List, Optional

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.models.custom_holiday import CustomHoliday
from app.schemas.custom_holiday import CustomHolidayCreate, CustomHolidayUpdate
from app.crud.base import CRUDBase


class CRUDCustomHoliday(CRUDBase[CustomHoliday, CustomHolidayCreate, CustomHolidayUpdate]):
    """カスタム祝日のCRUD操作"""

    def get_by_date(self, db: Session, *, date: datetime.date) -> Optional[CustomHoliday]:
        return db.query(CustomHoliday).filter(CustomHoliday.date == date).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[CustomHoliday]:
        return (
            db.query(CustomHoliday)
            .order_by(asc(CustomHoliday.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all(self, db: Session) -> List[CustomHoliday]:
        return db.query(CustomHoliday).order_by(asc(CustomHoliday.date)).all()


custom_holiday = CRUDCustomHoliday(CustomHoliday)
