import csv
from pathlib import Path
from collections import defaultdict
import calendar
import datetime
from typing import Dict, List, Optional, Any, DefaultDict

# 定数定義
CSV_FILE = Path("work_entries.csv")
LOCATION_TYPES = ["在宅", "出社", "出張"]


def import_csv_data(content: str) -> None:
    """CSVデータをファイルに保存する

    Args:
        content: CSVファイルの内容
    """
    with CSV_FILE.open("w", encoding="utf-8", newline="") as f:
        f.write(content)


def read_all_entries() -> Dict[str, Dict[str, str]]:
    """CSVファイルからすべてのエントリーを読み込む

    Returns:
        Dict[str, Dict[str, str]]: {user_name: {date: location}}形式のデータ
    """
    if not CSV_FILE.exists():
        return {}

    data = {}

    with CSV_FILE.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)  # 日付がヘッダーに格納されている
        dates = headers[1:]  # 最初の列はuser_name

        for row in reader:
            user_name = row[0]
            user_data = {}

            for i, location in enumerate(row[1:], 1):
                if location:  # 空欄でない場合のみ登録
                    date = dates[i - 1]
                    user_data[date] = location

            data[user_name] = user_data

    return data


def get_entries_by_date() -> DefaultDict[str, Dict[str, str]]:
    """日付ごとのエントリーを取得する

    Returns:
        DefaultDict[str, Dict[str, str]]: {date: {user_name: location}}形式のデータ
    """
    data = read_all_entries()
    date_entries = defaultdict(dict)

    # ユーザーごとのデータを日付ごとのデータに変換
    for user_name, user_data in data.items():
        for date, location in user_data.items():
            date_entries[date][user_name] = location

    return date_entries


def get_calendar_data(month: str) -> Dict[str, Any]:
    """月ごとのカレンダーデータを生成する

    Args:
        month: YYYY-MM形式の月指定

    Returns:
        Dict: カレンダー表示に必要なデータ
    """
    date_entries = get_entries_by_date()
    calendar_dict: DefaultDict[int, Dict[str, int]] = defaultdict(
        lambda: {location_type: 0 for location_type in LOCATION_TYPES}
    )

    # 月データの解析
    year, month_num = map(int, month.split("-"))

    # カレンダー用のデータ
    cal = calendar.monthcalendar(year, month_num)

    # エントリーデータの集計
    for date, entries in date_entries.items():
        if date.startswith(month):
            day = int(date.split("-")[2])
            for _, location in entries.items():
                calendar_dict[day][location] = calendar_dict[day].get(location, 0) + 1

    # 週ごとにまとめたカレンダーデータを作成
    calendar_weeks = []

    for week in cal:
        week_data = []
        for day in week:
            if day == 0:  # 0は月の範囲外の日
                week_data.append(None)
            else:
                day_data = {
                    "day": day,
                    "date": f"{month}-{day:02d}",
                    "home": calendar_dict[day].get("在宅", 0),
                    "office": calendar_dict[day].get("出社", 0),
                    "trip": calendar_dict[day].get("出張", 0),
                }
                week_data.append(day_data)
        calendar_weeks.append(week_data)

    # 前月・翌月の計算
    prev_month_date = datetime.date(year, month_num, 1) - datetime.timedelta(days=1)
    next_month_date = get_next_month_date(year, month_num)

    return {
        "weeks": calendar_weeks,
        "prev_month": f"{prev_month_date.year}-{prev_month_date.month:02d}",
        "next_month": f"{next_month_date.year}-{next_month_date.month:02d}",
        "month_name": f"{year}年{month_num}月",
    }


def get_next_month_date(year: int, month: int) -> datetime.date:
    """次の月の日付を取得する

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 翌月の日付
    """
    next_month = datetime.date(year, month, 28)
    # 確実に翌月にするため28日から始めて月が変わるまで加算
    while next_month.month == month:
        next_month += datetime.timedelta(days=1)
    return next_month


def get_day_data(day: str) -> Dict[str, List[str]]:
    """指定された日のデータを取得する

    Args:
        day: YYYY-MM-DD形式の日付

    Returns:
        Dict[str, List[str]]: 勤務場所ごとのユーザーリスト
    """
    date_entries = get_entries_by_date()
    detail = {location_type: [] for location_type in LOCATION_TYPES}

    if day in date_entries:
        for user_name, location in date_entries[day].items():
            detail[location].append(user_name)

    return detail


def get_user_data(username: str) -> List[Dict[str, str]]:
    """特定ユーザーのすべての記録を取得する

    Args:
        username: ユーザー名

    Returns:
        List[Dict[str, str]]: ユーザーのエントリーリスト
    """
    data = read_all_entries()

    if username not in data:
        return []

    user_entries = []
    for date, location in sorted(data[username].items()):
        user_entries.append({"user_name": username, "date": date, "location": location})

    return user_entries
