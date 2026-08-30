"""
カレンダーおよび日付ユーティリティ
============================

カレンダーと日付に関連する処理を行うユーティリティ関数を提供します。
"""

import datetime
import re
import calendar
from enum import Enum
from fastapi import Request
from typing import Dict, List, Any, Tuple, DefaultDict, Optional
from collections import defaultdict
from datetime import date, timedelta

from app.models.attendance import Attendance # Attendancesの型ヒント用に必要
from app.utils.ui_utils import generate_location_data
from app.utils.holiday_cache import is_holiday, get_holiday_name
from app.core.config import logger

# --- 設定 ---

# 日曜日を週の最初の日とする (0: 月曜始まり -> 6: 日曜始まり)
calendar.setfirstweekday(6)

# 日付フォーマット関連
DATE_FORMAT = "%Y-%m-%d"  # 標準の日付形式

class DateFormat(Enum):
    """サポートされる日付形式の列挙型"""
    DASH = "-"  # YYYY-MM-DD
    SLASH = "/"  # YYYY/MM/DD

DEFAULT_DATE_FORMAT = DateFormat.DASH


# --- 日付操作ユーティリティ ---

def format_date(date: datetime.date) -> str:
    """日付をYYYY-MM-DD形式にフォーマットします。

    Args:
        date: 日付オブジェクト

    Returns:
        str: YYYY-MM-DD形式の文字列
    """
    return date.strftime(DATE_FORMAT)

def format_date_jp(date_obj: Optional[datetime.date]) -> str:
    """日付を日本語形式（YYYY年M月D日(曜)）にフォーマットします。

    Args:
        date_obj: フォーマットする日付オブジェクト (Optional)

    Returns:
        str: 日本語形式の日付文字列、または date_obj が None の場合は空文字列
    """
    if date_obj is None:
        return ""
    weekdays = ["月", "火", "水", "木", "金", "土", "日"] # Pythonの weekday() に合わせる (0=月曜)
    weekday_str = weekdays[date_obj.weekday()]
    return f"{date_obj.year}年{date_obj.month}月{date_obj.day}日({weekday_str})"

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
    # 月フォーマットの検証
    if not re.match(r"^\d{4}[-/]\d{1,2}$", month):
        raise ValueError(f"無効な月フォーマット: {month}。YYYY-MMまたはYYYY/MM形式を使用してください。")

    # 区切り文字を検出
    separator = "-" if "-" in month else "/"
    parts = month.split(separator)

    try:
        year = int(parts[0])
        month_num = int(parts[1])

        # 年と月の妥当性チェック
        if year < 1900 or year > 2100:
            raise ValueError(f"年は1900-2100の範囲で指定してください: {year}")
        if month_num < 1 or month_num > 12:
            raise ValueError(f"月は1-12の範囲で指定してください: {month_num}")

        return year, month_num
    except (ValueError, IndexError) as e:
        raise ValueError(f"月の解析に失敗しました: {month}") from e

def get_prev_month_date(year: int, month: int) -> datetime.date:
    """前月の1日の日付を取得します

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 前月の1日の日付オブジェクト
    """
    if month == 1:
        return datetime.date(year - 1, 12, 1)
    else:
        return datetime.date(year, month - 1, 1)

def get_next_month_date(year: int, month: int) -> datetime.date:
    """翌月の1日の日付を取得します

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 翌月の1日の日付オブジェクト
    """
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    else:
        return datetime.date(year, month + 1, 1)


# --- 週単位処理関数 ---

def get_current_week_formatted() -> str:
    """現在の週をYYYY-MM-DD形式（月曜日の日付）で取得します。

    Returns:
        str: 現在の週の月曜日の日付（YYYY-MM-DD形式）
    """
    today = datetime.date.today()
    # 今日が何曜日かを取得（0=月曜日）
    weekday = today.weekday()
    # 今週の月曜日を計算
    monday = today - timedelta(days=weekday)
    return format_date(monday)

def parse_week(week_str: str) -> date:
    """週文字列（月曜日の日付）を日付オブジェクトに変換します

    Args:
        week_str: YYYY-MM-DD形式の月曜日の日付

    Returns:
        date: 月曜日の日付オブジェクト

    Raises:
        ValueError: 週のフォーマットが無効な場合
    """
    try:
        monday = datetime.datetime.strptime(week_str, "%Y-%m-%d").date()
        # 月曜日かどうかを確認
        if monday.weekday() != 0:
            raise ValueError(f"指定された日付は月曜日ではありません: {week_str}")
        return monday
    except ValueError as e:
        raise ValueError(f"無効な週フォーマット: {week_str}。YYYY-MM-DD形式の月曜日を指定してください。") from e

def get_prev_week_date(monday: date) -> date:
    """前週の月曜日の日付を取得します

    Args:
        monday: 基準となる月曜日の日付

    Returns:
        date: 前週の月曜日の日付オブジェクト
    """
    return monday - timedelta(days=7)

def get_next_week_date(monday: date) -> date:
    """翌週の月曜日の日付を取得します

    Args:
        monday: 基準となる月曜日の日付

    Returns:
        date: 翌週の月曜日の日付オブジェクト
    """
    return monday + timedelta(days=7)

def format_week_name(monday: date) -> str:
    """週の表示名を生成します（例：2025年1月第2週）

    Args:
        monday: 月曜日の日付

    Returns:
        str: 週の表示名
    """
    # その月の第何週かを計算
    first_day_of_month = monday.replace(day=1)
    first_monday = first_day_of_month
    while first_monday.weekday() != 0:
        first_monday += timedelta(days=1)
    
    # 月の最初の月曜日からの週数を計算
    week_number = ((monday - first_monday).days // 7) + 1
    
    return f"{monday.year}年{monday.month}月第{week_number}週"

def build_week_calendar_data(
    week_str: str,
    attendances: List[Attendance],
    attendance_counts: Dict[int, int],
    location_types: List[str]
) -> Dict[str, Any]:
    """
    特定の週のカレンダーデータを構築する（DBアクセスなし）

    Args:
        week_str: 週文字列（月曜日の日付、YYYY-MM-DD形式）
        attendances: 対象週の全勤怠レコードのリスト
        attendance_counts: 日付の日部分をキー、勤怠データ数を値とする辞書
        location_types: 利用可能な全勤怠種別名のソート済みリスト

    Returns:
        Dict[str, Any]: カレンダーデータ
                       エラー時は空のデータを返す可能性がある
    """
    try:
        # 対象週を解析（月曜日の日付）
        monday = parse_week(week_str)
        week_name = format_week_name(monday)

        # 週の7日間を生成（月曜日から日曜日）
        week_days = []
        for i in range(7):
            day_date = monday + timedelta(days=i)
            week_days.append(day_date)

        # 日付をキー、勤怠種別名をサブキーとするネストしたカウント辞書を初期化
        location_counts: DefaultDict[int, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 取得した勤怠レコードを日ごと・勤怠種別ごとに集計
        for attendance_record in attendances:
            day = attendance_record.date.day
            # locationリレーションから名前を取得
            location_name = str(attendance_record.location_info)
            location_counts[day][location_name] += 1

        # カレンダー表示用のデータ構造を構築（1週間分）
        week_data = []
        for day_date in week_days:
            date_str = format_date(day_date)
            day = day_date.day

            # 事前に一括取得したデータから、この日の総勤怠数を取得
            attendance_count = attendance_counts.get(day, 0)

            # 祝日判定と祝日名取得
            is_holiday_flag = is_holiday(day_date)
            holiday_name = get_holiday_name(day_date)

            day_data = {
                "day": day,
                "date": date_str,
                "has_data": attendance_count > 0,
                "is_holiday": is_holiday_flag,
                "holiday_name": holiday_name
            }

            # 各勤怠種別ごとの勤怠数を追加
            for loc_type in location_types:
                day_data[loc_type] = location_counts[day].get(loc_type, 0)

            week_data.append(day_data)

        # 前週と翌週の週文字列（月曜日の日付）を計算
        prev_week_monday = get_prev_week_date(monday)
        prev_week = format_date(prev_week_monday)

        next_week_monday = get_next_week_date(monday)
        next_week = format_date(next_week_monday)

        # UI表示用の勤怠種別データを生成
        locations_ui_data = generate_location_data(location_types)

        return {
            "week_name": week_name,
            "weeks": [week_data],  # 週単位なので1週間分のデータを配列に入れる
            "locations": locations_ui_data,
            "prev_week": prev_week,
            "next_week": next_week,
        }
    except ValueError as ve:
        logger.error(f"週フォーマット解析エラー: {str(ve)}")
        # エラー発生時は空のデータを返す
        return {"week_name": "", "weeks": [], "locations": [], "prev_week": "", "next_week": ""}
    except Exception as e:
        logger.error(f"週カレンダーデータ構築中に予期せぬエラーが発生しました: {str(e)}", exc_info=True)
        # エラー発生時は空のデータを返す
        return {"week_name": "", "weeks": [], "locations": [], "prev_week": "", "next_week": ""}


# --- カレンダー関連ユーティリティ ---

def build_calendar_data(
    month: str,
    attendances: List[Attendance],
    attendance_counts: Dict[int, int],
    location_types: List[str]
) -> Dict[str, Any]:
    """
    特定の月のカレンダーデータを構築する（DBアクセスなし）

    Args:
        month: 月文字列（YYYY-MM形式）
        attendances: 対象月の全勤怠レコードのリスト
        attendance_counts: 日付の日部分をキー、勤怠データ数を値とする辞書
        location_types: 利用可能な全勤怠種別名のソート済みリスト

    Returns:
        Dict[str, Any]: カレンダーデータ
                       エラー時は空のデータを返す可能性がある
    """
    try:
        # 対象月を解析
        year, month_num = parse_month(month)

        # 月名を生成（YYYY年M月形式）
        month_name = f"{year}年{month_num}月"

        # 月のカレンダーを生成
        cal = calendar.monthcalendar(year, month_num)

        # 日付をキー、勤怠種別名をサブキーとするネストしたカウント辞書を初期化
        location_counts: DefaultDict[int, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 取得した勤怠レコードを日ごと・勤怠種別ごとに集計
        for attendance_record in attendances:
            day = attendance_record.date.day
            # locationリレーションから名前を取得
            location_name = str(attendance_record.location_info)
            location_counts[day][location_name] += 1

        # カレンダー表示用のデータ構造を構築
        weeks = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    # calendar.monthcalendar は月の範囲外の日を0として返すため、
                    # UI側で非表示にするためのプレースホルダーデータを設定
                    day_data = {
                        "day": 0, # 日の値が0であればUI側で非表示にする想定
                        "date": "",
                        "has_data": False,
                    }
                    # プレースホルダーにも勤怠種別カラムは用意 (UIの構造を合わせるため)
                    for loc_type in location_types:
                        day_data[loc_type] = 0

                    week_data.append(day_data)
                else:
                    # 有効な日付の場合、詳細データを設定
                    current_date = date(year, month_num, day)
                    date_str = format_date(current_date)

                    # 事前に一括取得したデータから、この日の総勤怠数を取得 (引数のattendance_countsを使用)
                    attendance_count = attendance_counts.get(day, 0)

                    # 祝日判定と祝日名取得
                    is_holiday_flag = is_holiday(current_date)
                    holiday_name = get_holiday_name(current_date)

                    day_data = {
                        "day": day,
                        "date": date_str,
                        "has_data": attendance_count > 0,
                        "is_holiday": is_holiday_flag,
                        "holiday_name": holiday_name
                    }

                    # 各勤怠種別ごとの勤怠数を追加 (計算済みのlocation_countsを使用)
                    for loc_type in location_types:
                        day_data[loc_type] = location_counts[day].get(loc_type, 0)

                    week_data.append(day_data)

            weeks.append(week_data)

        # 前月と翌月の月文字列を計算
        prev_month_date = get_prev_month_date(year, month_num)
        prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"

        next_month_date = get_next_month_date(year, month_num)
        next_month = f"{next_month_date.year}-{next_month_date.month:02d}"

        # UI表示用の勤怠種別データを生成
        locations_ui_data = generate_location_data(location_types)

        return {
            "month_name": month_name,
            "weeks": weeks,
            "locations": locations_ui_data,
            "prev_month": prev_month,
            "next_month": next_month,
        }
    except ValueError as ve:
        logger.error(f"月フォーマット解析エラー: {str(ve)}")
        # エラー発生時は空のデータを返す
        return {"month_name": "エラー", "weeks": [], "locations": [], "prev_month": "", "next_month": ""}
    except Exception as e:
        logger.error(f"カレンダーデータ構築中に予期せぬエラーが発生しました: {str(e)}", exc_info=True)
        # エラー発生時は空のデータを返す
        return {"month_name": "エラー", "weeks": [], "locations": [], "prev_month": "", "next_month": ""}

