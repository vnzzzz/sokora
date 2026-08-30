"""
日付ユーティリティモジュール
=====================

日付操作や変換を行うユーティリティ関数を提供します。
"""

import datetime
import re
from enum import Enum
from fastapi import Request
from typing import Optional, Tuple, Dict, Any


class DateFormat(Enum):
    """サポートされる日付形式の列挙型"""
    DASH = "-"  # YYYY-MM-DD
    SLASH = "/"  # YYYY/MM/DD


# 日付ユーティリティの設定値
DATE_FORMAT = "%Y-%m-%d"  # 標準の日付形式
DEFAULT_DATE_FORMAT = DateFormat.DASH


def format_date(date: datetime.date) -> str:
    """日付をYYYY-MM-DD形式にフォーマットします。

    Args:
        date: 日付オブジェクト

    Returns:
        str: YYYY-MM-DD形式の文字列
    """
    return date.strftime(DATE_FORMAT)


def get_today_formatted() -> str:
    """今日の日付をYYYY-MM-DD形式で取得します。

    Returns:
        str: 今日の日付（YYYY-MM-DD形式）
    """
    return format_date(datetime.date.today())


def get_current_month_formatted() -> str:
    """現在の月をYYYY-MM形式で取得します。

    Returns:
        str: 現在の月（YYYY-MM形式）
    """
    today = datetime.date.today()
    return f"{today.year}-{today.month:02d}"


def get_last_viewed_date(request: Request) -> str:
    """最後に表示された日付を取得します。

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
        try:
            date_part = referer.split("/api/day/")[-1].split("?")[0].split("/")[0]
            # 日付形式の検証
            if parse_date(date_part):
                return date_part
        except (IndexError, ValueError):
            pass
    return get_today_formatted()


def _detect_date_format(date_str: str) -> Optional[DateFormat]:
    """日付文字列のフォーマットを検出します。

    Args:
        date_str: 日付文字列

    Returns:
        Optional[DateFormat]: 検出された日付フォーマット、検出できない場合はNone
    """
    if "-" in date_str:
        return DateFormat.DASH
    elif "/" in date_str:
        return DateFormat.SLASH
    return None


def _split_date_string(date_str: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """日付文字列を年、月、日に分解します。

    Args:
        date_str: 日付文字列（YYYY-MM-DDまたはYYYY/MM/DD形式）

    Returns:
        Tuple[Optional[int], Optional[int], Optional[int]]: 年、月、日の整数値のタプル
        分解できない場合はNoneが含まれる
    """
    format_type = _detect_date_format(date_str)
    if not format_type:
        return None, None, None
        
    try:
        parts = date_str.split(format_type.value)
        if len(parts) != 3:
            return None, None, None
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None, None, None


def parse_date(date_str: str) -> Optional[datetime.date]:
    """日付文字列を日付オブジェクトに変換します。

    対応フォーマット:
    - YYYY-MM-DD（2025-04-01または2025-4-1）
    - YYYY/MM/DD（2025/04/01または2025/4/1）

    Args:
        date_str: 対応フォーマットの日付文字列

    Returns:
        Optional[datetime.date]: 変換された日付オブジェクト、変換に失敗した場合はNone
    """
    year, month, day = _split_date_string(date_str)
    
    if year is None or month is None or day is None:
        return None
        
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def normalize_date_format(date_str: str) -> str:
    """様々な日付形式をYYYY-MM-DDに正規化します。

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
