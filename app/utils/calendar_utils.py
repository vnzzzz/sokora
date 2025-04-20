"""
カレンダーユーティリティ
-----------------

カレンダー処理のためのユーティリティ関数
"""

import datetime
import calendar
import jpholiday  # type: ignore
from typing import Dict, List, Any, Tuple, DefaultDict
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session

# 日曜日を週の最初の日とするカレンダー設定（0: 月曜始まり → 6: 日曜始まり）
calendar.setfirstweekday(6)


def parse_month(month: str) -> Tuple[int, int]:
    """文字列を年と月に解析します

    対応フォーマット:
    - YYYY-MM形式
    - YYYY/MM形式

    Args:
        month: YYYY-MMまたはYYYY/MM形式の月

    Returns:
        Tuple[int, int]: (年, 月)のタプル

    Raises:
        ValueError: 月のフォーマットが無効な場合
    """
    try:
        if "-" in month:
            year, month_num = map(int, month.split("-"))
        elif "/" in month:
            year, month_num = map(int, month.split("/"))
        else:
            raise ValueError(
                f"無効な月フォーマット: {month}。YYYY-MMまたはYYYY/MM形式を使用してください。"
            )

        if month_num < 1 or month_num > 12:
            raise ValueError(f"無効な月番号: {month_num}")
        return year, month_num
    except Exception:
        raise ValueError(
            f"無効な月フォーマット: {month}。YYYY-MMまたはYYYY/MM形式を使用してください。"
        )


def get_prev_month_date(year: int, month: int) -> datetime.date:
    """前月の日付を取得します

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 前月の日付オブジェクト
    """
    if month == 1:
        return datetime.date(year - 1, 12, 1)
    return datetime.date(year, month - 1, 1)


def get_next_month_date(year: int, month: int) -> datetime.date:
    """翌月の日付を取得します

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 翌月の日付オブジェクト
    """
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    return datetime.date(year, month + 1, 1)


def is_holiday(date_obj: date) -> bool:
    """与えられた日付が祝日かどうかを判定します

    Args:
        date_obj: 判定する日付

    Returns:
        bool: 祝日の場合はTrue、そうでない場合はFalse
    """
    return jpholiday.is_holiday(date_obj)


def get_holiday_name(date_obj: date) -> str:
    """与えられた日付の祝日名を取得します

    Args:
        date_obj: 判定する日付

    Returns:
        str: 祝日名（祝日でない場合は空文字列）
    """
    holiday = jpholiday.is_holiday_name(date_obj)
    return holiday if holiday else ""


def build_calendar_data(db: Session, month: str) -> Dict[str, Any]:
    """
    特定の月のカレンダーデータを構築する

    Args:
        db: データベースセッション
        month: 月文字列 (YYYY-MM)

    Returns:
        Dict[str, Any]: カレンダーデータ
    """
    # 循環参照を避けるために遅延インポート
    from app.crud.location import location
    from app.crud.calendar import calendar_crud
    from app.utils.ui_utils import generate_location_data
    from app.core.config import logger
    
    try:
        # 月を解析
        year, month_num = parse_month(month)
        month_name = f"{year}年{month_num}月"

        # その月のカレンダーを作成
        cal = calendar.monthcalendar(year, month_num)

        # 勤務場所のリストを取得
        location_types = location.get_all_locations(db)

        # 日ごとの勤務場所カウントを初期化
        location_counts: DefaultDict[int, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 月の初日と末日を取得
        first_day = date(year, month_num, 1)
        last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

        # この月の全勤怠レコードを取得
        attendances = calendar_crud.get_month_attendances(
            db, first_day=first_day, last_day=last_day
        )

        # 勤務場所ごとのカウントを集計
        for attendance in attendances:
            day = attendance.date.day
            location_name = str(attendance.location_info)  # 勤務場所の文字列表現を取得
            location_counts[day][location_name] += 1

        # 各週と日に勤怠情報を付与
        weeks = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    # 月の範囲外の日
                    # 同じデータ構造で日の値だけ0に
                    day_data = {
                        "day": 0,  # 0日
                        "date": "",
                        "has_data": False,
                    }
                    
                    # 各勤務場所のカウントを0で追加
                    for loc_type in location_types:
                        day_data[loc_type] = 0
                        
                    week_data.append(day_data)
                else:
                    current_date = date(year, month_num, day)
                    date_str = current_date.strftime("%Y-%m-%d")

                    # この日の勤怠データをカウント
                    attendance_count = calendar_crud.count_day_attendances(
                        db, target_date=current_date
                    )

                    # 祝日情報を取得
                    is_holiday_flag = is_holiday(current_date)
                    holiday_name = get_holiday_name(current_date)

                    day_data = {
                        "day": day,
                        "date": date_str,
                        "has_data": attendance_count > 0,
                        "is_holiday": is_holiday_flag,
                        "holiday_name": holiday_name
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
        logger.error(f"Error building calendar data: {str(e)}")
        return {"month_name": "", "weeks": [], "locations": []}
