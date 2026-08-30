"""
カレンダーユーティリティ
-----------------

カレンダー処理のためのユーティリティ関数
"""

import datetime
import calendar
from typing import Dict, List, Any, Tuple

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
