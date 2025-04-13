import datetime
from fastapi import Request
from typing import Optional


def format_date(date: datetime.date) -> str:
    """日付をYYYY-MM-DD形式に整形する

    Args:
        date: 日付オブジェクト

    Returns:
        str: YYYY-MM-DD形式の文字列
    """
    return date.strftime("%Y-%m-%d")


def get_today_formatted() -> str:
    """今日の日付をYYYY-MM-DD形式で取得する

    Returns:
        str: 今日の日付（YYYY-MM-DD形式）
    """
    return format_date(datetime.date.today())


def get_current_month_formatted() -> str:
    """今月をYYYY-MM形式で取得する

    Returns:
        str: 今月（YYYY-MM形式）
    """
    today = datetime.date.today()
    return f"{today.year}-{today.month:02d}"


def get_last_viewed_date(request: Request) -> str:
    """最後に表示した日付を取得する

    リクエストのRefererヘッダーから最後に表示した日付を抽出する。
    '/api/day/' パスの後ろに日付がある場合はその日付を、
    そうでない場合は今日の日付を返す。

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        str: 最後に表示した日付（YYYY-MM-DD形式）
    """
    referer = request.headers.get("referer", "")
    if "/api/day/" in referer:
        return referer.split("/api/day/")[-1].split("?")[0]
    return get_today_formatted()


def parse_date(date_str: str) -> Optional[datetime.date]:
    """YYYY-MM-DD形式の文字列を日付オブジェクトに変換する

    Args:
        date_str: YYYY-MM-DD形式の日付文字列

    Returns:
        Optional[datetime.date]: 変換された日付オブジェクト、または変換失敗時はNone
    """
    try:
        year, month, day = map(int, date_str.split("-"))
        return datetime.date(year, month, day)
    except (ValueError, IndexError):
        return None
