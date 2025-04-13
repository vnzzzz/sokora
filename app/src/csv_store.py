import csv
from pathlib import Path
from collections import defaultdict
import calendar
import datetime
import os
from typing import Dict, List, Optional, Any, DefaultDict, Tuple


# 定数定義
LOCATION_TYPES = ["在宅", "出社", "出張"]


def get_csv_file_path() -> Path:
    """CSV_FILEの場所を特定する関数

    Returns:
        Path: CSVファイルのパス
    """
    possible_paths = [
        "work_entries.csv",  # 基本パス
        os.path.join(os.getcwd(), "work_entries.csv"),  # カレントディレクトリ
        os.path.join(os.getcwd(), "data", "work_entries.csv"),  # data/ディレクトリ
        os.path.join(
            os.path.dirname(os.getcwd()), "data", "work_entries.csv"
        ),  # 親ディレクトリのdata/
        os.path.join(os.getcwd(), "app", "work_entries.csv"),  # Docker環境用
        os.path.join(
            os.getcwd(), "app", "data", "work_entries.csv"
        ),  # Docker環境用data/
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return Path(path)

    # 存在しない場合は基本パスを返す（新規作成用）
    return Path("work_entries.csv")


def import_csv_data(content: str) -> None:
    """CSVデータをファイルに保存する

    Args:
        content: CSVファイルの内容

    Raises:
        IOError: ファイルの書き込みに失敗した場合
    """
    try:
        with get_csv_file_path().open("w", encoding="utf-8", newline="") as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"CSVデータの書き込みに失敗しました: {str(e)}")


def read_all_entries() -> Dict[str, Dict[str, str]]:
    """CSVファイルからすべてのエントリーを読み込む

    Returns:
        Dict[str, Dict[str, str]]: {user_name: {date: location}}形式のデータ

    Raises:
        FileNotFoundError: CSVファイルが存在しない場合
    """
    csv_path = get_csv_file_path()
    if not csv_path.exists():
        return {}

    data: Dict[str, Dict[str, str]] = {}

    try:
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)  # 日付がヘッダーに格納されている
            dates = headers[1:]  # 最初の列はuser_name

            for row in reader:
                user_name = row[0]
                user_data: Dict[str, str] = {}

                for i, location in enumerate(row[1:], 1):
                    if location and i <= len(
                        dates
                    ):  # 空欄でない場合かつインデックスが有効な場合のみ登録
                        date = dates[i - 1]
                        user_data[date] = location

                data[user_name] = user_data
    except Exception as e:
        raise IOError(f"CSVデータの読み込みに失敗しました: {str(e)}")

    return data


def get_entries_by_date() -> DefaultDict[str, Dict[str, str]]:
    """日付ごとのエントリーを取得する

    Returns:
        DefaultDict[str, Dict[str, str]]: {date: {user_name: location}}形式のデータ
    """
    data = read_all_entries()
    date_entries: DefaultDict[str, Dict[str, str]] = defaultdict(dict)

    # ユーザーごとのデータを日付ごとのデータに変換
    for user_name, user_data in data.items():
        for date, location in user_data.items():
            date_entries[date][user_name] = location

    return date_entries


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


def get_calendar_data(month: str) -> Dict[str, Any]:
    """月ごとのカレンダーデータを生成する

    Args:
        month: YYYY-MM形式の月指定

    Returns:
        Dict: カレンダー表示に必要なデータ

    Raises:
        ValueError: 無効な月フォーマットの場合
    """
    date_entries = get_entries_by_date()
    calendar_dict: DefaultDict[int, Dict[str, int]] = defaultdict(
        lambda: {location_type: 0 for location_type in LOCATION_TYPES}
    )

    # 月データの解析
    year, month_num = parse_month(month)

    # カレンダー用のデータ
    cal = calendar.monthcalendar(year, month_num)

    # エントリーデータの集計
    for date, entries in date_entries.items():
        if date.startswith(month):
            try:
                day = int(date.split("-")[2])
                for _, location in entries.items():
                    if location in LOCATION_TYPES:
                        calendar_dict[day][location] = (
                            calendar_dict[day].get(location, 0) + 1
                        )
            except (IndexError, ValueError):
                continue  # 無効な日付形式はスキップ

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
    prev_month_date = get_prev_month_date(year, month_num)
    next_month_date = get_next_month_date(year, month_num)

    return {
        "weeks": calendar_weeks,
        "prev_month": f"{prev_month_date.year}-{prev_month_date.month:02d}",
        "next_month": f"{next_month_date.year}-{next_month_date.month:02d}",
        "month_name": f"{year}年{month_num}月",
    }


def get_prev_month_date(year: int, month: int) -> datetime.date:
    """前の月の日付を取得する

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 前月の日付
    """
    if month == 1:
        # 1月の場合は前年の12月
        return datetime.date(year - 1, 12, 1)
    else:
        # それ以外は同じ年の前月
        return datetime.date(year, month - 1, 1)


def get_next_month_date(year: int, month: int) -> datetime.date:
    """次の月の日付を取得する

    Args:
        year: 年
        month: 月

    Returns:
        datetime.date: 翌月の日付
    """
    if month == 12:
        # 12月の場合は翌年の1月
        return datetime.date(year + 1, 1, 1)
    else:
        # それ以外は同じ年の翌月
        return datetime.date(year, month + 1, 1)


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
            if location in LOCATION_TYPES:
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
