"""
カレンダーユーティリティ
-----------------

カレンダー処理に関連するユーティリティ関数
"""

import datetime
import calendar
from collections import defaultdict
from typing import Dict, List, Any, Tuple, DefaultDict

# 日本のカレンダー設定（0:月曜始まり → 6:日曜始まり）
calendar.setfirstweekday(6)


def parse_month(month: str) -> Tuple[int, int]:
    """YYYY-MM形式の文字列を年と月に分解する

    Args:
        month: YYYY-MM形式の月指定

    Returns:
        Tuple[int, int]: (年, 月)のタプル

    Raises:
        ValueError: 無効な月フォーマットの場合
    """
    try:
        year, month_num = map(int, month.split("-"))
        if month_num < 1 or month_num > 12:
            raise ValueError(f"無効な月番号: {month_num}")
        return year, month_num
    except Exception:
        raise ValueError(
            f"無効な月フォーマット: {month}。YYYY-MM形式で指定してください。"
        )


def get_prev_month_date(year: int, month: int) -> datetime.date:
    """前月の日付を取得する

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
    """翌月の日付を取得する

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 翌月の日付オブジェクト
    """
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    return datetime.date(year, month + 1, 1)


def generate_location_data(location_types: List[str]) -> List[Dict[str, str]]:
    """勤務場所のスタイル情報を生成する

    Args:
        location_types: 勤務場所の種類のリスト

    Returns:
        List[Dict[str, str]]: 勤務場所とそのスタイル情報のリスト
    """
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []

    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "color": f"text-{colors[color_index]}",
                "key": loc_type,
                "badge": colors[color_index],
            }
        )

    return locations


def create_calendar_weeks(
    cal_data: List[List[int]],
    month: str,
    calendar_dict: DefaultDict[int, Dict[str, int]],
    location_types: List[str],
) -> List[List[Dict]]:
    """週ごとにまとめたカレンダーデータを作成する

    Args:
        cal_data: calendar.monthcalendarの結果
        month: YYYY-MM形式の月指定
        calendar_dict: 日ごとの勤務場所カウント
        location_types: 勤務場所の種類のリスト

    Returns:
        List[List[Dict]]: 週ごとのカレンダーデータ
    """
    calendar_weeks = []

    for week in cal_data:
        week_data = []
        for day in week:
            if day == 0:  # 0は月の範囲外の日
                week_data.append(None)
            else:
                day_data = {
                    "day": day,
                    "date": f"{month}-{day:02d}",
                }
                # 各勤務場所タイプのカウントをデータに追加
                for loc_type in location_types:
                    day_data[loc_type] = calendar_dict[day].get(loc_type, 0)
                week_data.append(day_data)
        calendar_weeks.append(week_data)

    return calendar_weeks
