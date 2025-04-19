import datetime
import re
from fastapi import Request
from typing import Optional


def format_date(date: datetime.date) -> str:
    """日付をYYYY-MM-DD形式にフォーマットします

    Args:
        date: 日付オブジェクト

    Returns:
        str: YYYY-MM-DD形式の文字列
    """
    return date.strftime("%Y-%m-%d")


def get_today_formatted() -> str:
    """今日の日付をYYYY-MM-DD形式で取得します

    Returns:
        str: 今日の日付（YYYY-MM-DD形式）
    """
    return format_date(datetime.date.today())


def get_current_month_formatted() -> str:
    """現在の月をYYYY-MM形式で取得します

    Returns:
        str: 現在の月（YYYY-MM形式）
    """
    today = datetime.date.today()
    return f"{today.year}-{today.month:02d}"


def get_last_viewed_date(request: Request) -> str:
    """最後に表示された日付を取得します

    リクエストのRefererヘッダーから最後に表示された日付を抽出します。
    '/api/day/'パスの後に日付がある場合はその日付を返し、
    そうでない場合は今日の日付を返します。

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        str: 最後に表示された日付（YYYY-MM-DD形式）
    """
    referer = request.headers.get("referer", "")
    if "/api/day/" in referer:
        return referer.split("/api/day/")[-1].split("?")[0]
    return get_today_formatted()


def parse_date(date_str: str) -> Optional[datetime.date]:
    """日付文字列を日付オブジェクトに変換します

    対応フォーマット:
    - YYYY-MM-DD（2025-04-01または2025-4-1）
    - YYYY/MM/DD（2025/04/01または2025/4/1）

    Args:
        date_str: 対応フォーマットの日付文字列

    Returns:
        Optional[datetime.date]: 変換された日付オブジェクト、変換に失敗した場合はNone
    """
    try:
        # まずYYYY-MM-DD形式を試す
        if "-" in date_str:
            year, month, day = map(int, date_str.split("-"))
            return datetime.date(year, month, day)
        # YYYY/MM/DD形式を試す
        elif "/" in date_str:
            year, month, day = map(int, date_str.split("/"))
            return datetime.date(year, month, day)
        return None
    except (ValueError, IndexError):
        return None


def normalize_date_format(date_str: str) -> str:
    """様々な日付形式をYYYY-MM-DDに正規化します

    対応フォーマット:
    - YYYY-MM-DD（2025-04-01または2025-4-1）
    - YYYY/MM/DD（2025/04/01または2025/4/1）

    Args:
        date_str: 対応フォーマットの日付文字列

    Returns:
        str: YYYY-MM-DD形式に正規化された日付文字列、または
             変換に失敗した場合は元の文字列
    """
    date_obj = parse_date(date_str)
    if date_obj:
        return format_date(date_obj)
    return date_str
