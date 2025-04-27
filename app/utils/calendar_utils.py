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
        # 対象月を解析 (YYYY-MM形式)
        year, month_num = parse_month(month)
        month_name = f"{year}年{month_num}月"

        # Python標準のcalendarモジュールでその月のカレンダー構造を取得 (週ごとの日のリスト)
        cal = calendar.monthcalendar(year, month_num)

        # データベースから利用可能な全勤務場所名を取得
        location_types = location.get_all_locations(db)

        # 日付をキー、勤務場所名をサブキーとするネストしたカウント辞書を初期化
        location_counts: DefaultDict[int, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))

        # 対象月の初日と最終日を計算
        first_day = date(year, month_num, 1)
        last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

        # 対象月期間の全勤怠レコードをデータベースから取得
        attendances = calendar_crud.get_month_attendances(
            db, first_day=first_day, last_day=last_day
        )

        # 取得した勤怠レコードを日ごと・勤務場所ごとに集計
        for attendance in attendances:
            day = attendance.date.day
            location_name = str(attendance.location_info) # locationリレーションから名前を取得
            location_counts[day][location_name] += 1

        # 日ごとの総勤怠データ数を一括で取得 (パフォーマンスのため)
        attendance_counts = calendar_crud.get_month_attendance_counts(
            db, first_day=first_day, last_day=last_day
        )

        # カレンダー表示用のデータ構造を構築 (週ごとのリスト)
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
                    # プレースホルダーにも勤務場所カラムは用意 (UIの構造を合わせるため)
                    for loc_type in location_types:
                        day_data[loc_type] = 0

                    week_data.append(day_data)
                else:
                    # 有効な日付の場合、詳細データを設定
                    current_date = date(year, month_num, day)
                    date_str = current_date.strftime("%Y-%m-%d")

                    # 事前に一括取得したデータから、この日の総勤怠数を取得
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

                    # 各勤務場所ごとの勤怠数を追加
                    for loc_type in location_types:
                        day_data[loc_type] = location_counts[day].get(loc_type, 0)

                    week_data.append(day_data)
            weeks.append(week_data)

        # 前月と翌月の年月文字列 (YYYY-MM) を計算
        # 前月の計算: 対象月の1日から1日引く
        prev_month_date = date(year, month_num, 1) - timedelta(days=1)
        prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"

        # 翌月の計算: 対象月の最終日から1日足す (monthrangeで正確な最終日を取得)
        last_day_of_month = calendar.monthrange(year, month_num)[1]
        next_month_date = date(year, month_num, last_day_of_month) + timedelta(days=1)
        next_month = f"{next_month_date.year}-{next_month_date.month:02d}"

        # UI表示用の勤務場所データ (色情報などを含む) を生成
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
        return {"month_name": "", "weeks": [], "locations": [], "prev_month": "", "next_month": ""}
    except Exception as e:
        logger.error(f"カレンダーデータ構築中に予期せぬエラーが発生しました: {str(e)}", exc_info=True)
        # エラー発生時は空のデータを返す
        return {"month_name": "", "weeks": [], "locations": [], "prev_month": "", "next_month": ""}


# 遅延インポートを解消するためのダミー呼び出し（型チェック用）
if __name__ == "__main__":
    # このブロックは通常実行されない
    from app.crud.location import location
    from app.crud.calendar import calendar_crud
    from app.utils.ui_utils import generate_location_data
    from app.core.config import logger
