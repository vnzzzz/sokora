import csv
from pathlib import Path
from collections import defaultdict
import calendar
import datetime

CSV_FILE = Path("work_entries.csv")


def import_csv_data(content: str):
    with CSV_FILE.open("w", encoding="utf-8", newline="") as f:
        f.write(content)


def read_all_entries():
    """新しいCSV形式からデータを読み込む"""
    if not CSV_FILE.exists():
        return {}

    # 新しい形式: {user_name: {date: location}}
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


def get_entries_by_date():
    """日付ごとのエントリーを取得する"""
    data = read_all_entries()
    date_entries = defaultdict(dict)

    # ユーザーごとのデータを日付ごとのデータに変換
    for user_name, user_data in data.items():
        for date, location in user_data.items():
            date_entries[date][user_name] = location

    return date_entries


def get_calendar_data(month: str):
    date_entries = get_entries_by_date()
    calendar_dict = defaultdict(lambda: {"在宅": 0, "出社": 0, "出張": 0})

    # 月データの解析
    year, month_num = map(int, month.split("-"))

    # カレンダー用のデータ
    cal = calendar.monthcalendar(year, month_num)

    # エントリーデータの集計
    for date, entries in date_entries.items():
        if date.startswith(month):
            day = int(date.split("-")[2])
            for user, location in entries.items():
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
    prev_month = datetime.date(year, month_num, 1) - datetime.timedelta(days=1)
    next_month = datetime.date(year, month_num, 28)
    # 確実に翌月にするため28日から始めて月が変わるまで加算
    while next_month.month == month_num:
        next_month += datetime.timedelta(days=1)

    return {
        "weeks": calendar_weeks,
        "prev_month": f"{prev_month.year}-{prev_month.month:02d}",
        "next_month": f"{next_month.year}-{next_month.month:02d}",
        "month_name": f"{year}年{month_num}月",
    }


def get_day_data(day: str):
    date_entries = get_entries_by_date()
    detail = {"在宅": [], "出社": [], "出張": []}

    if day in date_entries:
        for user_name, location in date_entries[day].items():
            detail.setdefault(location, []).append(user_name)

    return detail


def get_user_data(username: str):
    data = read_all_entries()

    if username not in data:
        return []

    user_entries = []
    for date, location in sorted(data[username].items()):
        user_entries.append(
            {"user_name": username, "work_date": date, "location": location}
        )

    return user_entries
