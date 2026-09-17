"""
カスタム祝日CRUD操作
"""

import datetime
from typing import List, Optional

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.custom_holiday import CustomHoliday
from app.schemas.custom_holiday import CustomHolidayCreate, CustomHolidayUpdate


class CRUDCustomHoliday(
    CRUDBase[CustomHoliday, CustomHolidayCreate, CustomHolidayUpdate]
):
    """カスタム祝日のCRUD操作。"""

    def get_by_date(
        self, db: Session, *, date: datetime.date
    ) -> Optional[CustomHoliday]:
        """日付でカスタム祝日を1件取得する。

        Args:
            db: DB session。
            date: 検索対象日。

        Returns:
            一致するカスタム祝日。存在しない場合は`None`。
        """
        return db.query(CustomHoliday).filter(CustomHoliday.date == date).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[CustomHoliday]:
        """日付順でカスタム祝日一覧を取得する。

        Args:
            db: DB session。
            skip: 先頭からskipする件数。
            limit: 最大取得件数。

        Returns:
            pagination適用済みのカスタム祝日list。
        """
        return (
            db.query(CustomHoliday)
            .order_by(asc(CustomHoliday.date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(self, db: Session) -> List[CustomHoliday]:
        """全カスタム祝日を日付順で取得する。

        Args:
            db: DB session。

        Returns:
            全カスタム祝日のlist。
        """
        return db.query(CustomHoliday).order_by(asc(CustomHoliday.date)).all()


custom_holiday = CRUDCustomHoliday(CustomHoliday)
