"""
Calendar operations
===============

Calendar data manipulation operations.
"""

import calendar
from typing import Dict, Any, List
from datetime import date
from sqlalchemy.orm import Session

from ..models.attendance import Attendance
from ..utils.calendar_utils import parse_month


# Calendar settings for Sunday as first day of week (0: Monday start → 6: Sunday start)
calendar.setfirstweekday(6)


class CRUDCalendar:
    """カレンダー関連の操作クラス"""

    def get_calendar_data(self, db: Session, *, month: str) -> Dict[str, Any]:
        """
        特定の月のカレンダーデータを取得

        Args:
            db: データベースセッション
            month: 月文字列 (YYYY-MM)

        Returns:
            Dict[str, Any]: カレンダーデータ
        """
        try:
            # 月を解析
            year, month_num = parse_month(month)

            # 月の初日と末日を取得
            first_day = date(year, month_num, 1)
            last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            # 月名を取得
            month_name = f"{year}年{month_num}月"

            # カレンダーデータを取得
            cal = calendar.monthcalendar(year, month_num)

            # 週ごとのデータを準備
            weeks = []
            for week in cal:
                week_data = []
                for day in week:
                    if day == 0:
                        # 月の範囲外の日
                        week_data.append({"day": 0, "date": "", "has_data": False})
                    else:
                        current_date = date(year, month_num, day)
                        date_str = current_date.strftime("%Y-%m-%d")

                        # この日の出席データをカウント
                        attendance_count = (
                            db.query(Attendance)
                            .filter(Attendance.date == current_date)
                            .count()
                        )

                        week_data.append(
                            {
                                "day": day,
                                "date": date_str,
                                "has_data": attendance_count > 0,
                            }
                        )
                weeks.append(week_data)

            return {"month_name": month_name, "weeks": weeks}
        except Exception:
            return {"month_name": "", "weeks": []}


calendar_crud = CRUDCalendar()
