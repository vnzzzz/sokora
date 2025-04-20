"""
Calendar operations
===============

Calendar data manipulation operations.
"""

import calendar
from typing import Dict, Any, List
from datetime import date, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

from ..models.attendance import Attendance
from ..models.user import User
from ..crud.location import location as location_crud
from ..utils.calendar_utils import parse_month
from ..utils.ui_utils import generate_location_data
from ..core.config import logger


# Calendar settings for Sunday as first day of week (0: Monday start → 6: Sunday start)
calendar.setfirstweekday(6)


class CRUDCalendar:
    """カレンダー関連のデータアクセス操作クラス"""

    def get_month_attendances(
        self, db: Session, *, first_day: date, last_day: date
    ) -> List[Attendance]:
        """
        指定した期間内の勤怠データを取得

        Args:
            db: データベースセッション
            first_day: 期間の開始日
            last_day: 期間の終了日

        Returns:
            List[Attendance]: 勤怠データのリスト
        """
        try:
            return (
                db.query(Attendance)
                .filter(Attendance.date >= first_day, Attendance.date <= last_day)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting month attendances: {str(e)}")
            return []

    def count_day_attendances(self, db: Session, *, target_date: date) -> int:
        """
        指定した日の勤怠データ数を取得

        Args:
            db: データベースセッション
            target_date: 対象日

        Returns:
            int: 勤怠データ数
        """
        try:
            return db.query(Attendance).filter(Attendance.date == target_date).count()
        except Exception as e:
            logger.error(f"Error counting day attendances: {str(e)}")
            return 0


calendar_crud = CRUDCalendar()
