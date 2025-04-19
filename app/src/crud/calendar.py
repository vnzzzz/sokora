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
from ..utils.calendar_utils import parse_month, generate_location_data
from ..core.config import logger


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
            month_name = f"{year}年{month_num}月"

            # その月のカレンダーを作成
            cal = calendar.monthcalendar(year, month_num)

            # 勤務場所のリストを取得
            location_types = location_crud.get_all_locations(db)

            # 日ごとの勤務場所カウントを初期化
            location_counts = defaultdict(lambda: defaultdict(int))

            # 月の初日と末日を取得
            first_day = date(year, month_num, 1)
            last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            # この月の全出席レコードを取得
            attendances = (
                db.query(Attendance)
                .filter(Attendance.date >= first_day, Attendance.date <= last_day)
                .all()
            )

            # 勤務場所ごとのカウントを集計
            for attendance in attendances:
                day = attendance.date.day
                location = attendance.location
                location_counts[day][location] += 1

            # 各週と日に出席情報を付与
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

                        day_data = {
                            "day": day,
                            "date": date_str,
                            "has_data": attendance_count > 0,
                        }

                        # 各勤務場所のカウントを追加
                        for loc_type in location_types:
                            day_data[loc_type] = location_counts[day].get(loc_type, 0)

                        week_data.append(day_data)
                weeks.append(week_data)

            # 前月と翌月の情報を計算
            prev_month_date = date(year, month_num, 1) - timedelta(days=1)
            prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"

            next_month_date = date(year, month_num, 28)  # 月末を超えても翌月になる
            if next_month_date.month == month_num:  # まだ同じ月の場合は日付を増やす
                next_month_date = next_month_date.replace(
                    day=calendar.monthrange(year, month_num)[1]
                ) + timedelta(days=1)
            next_month = f"{next_month_date.year}-{next_month_date.month:02d}"

            # 勤務場所の表示データを生成
            locations = generate_location_data(location_types)

            return {
                "month_name": month_name,
                "weeks": weeks,
                "locations": locations,
                "prev_month": prev_month,
                "next_month": next_month,
            }
        except Exception as e:
            logger.error(f"Error getting calendar data: {str(e)}")
            return {"month_name": "", "weeks": [], "locations": []}


calendar_crud = CRUDCalendar()
