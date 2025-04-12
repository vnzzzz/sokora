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
    if not CSV_FILE.exists():
        return []
    with CSV_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_calendar_data(month: str):
    entries = read_all_entries()
    calendar_dict = defaultdict(lambda: {"在宅": 0, "出社": 0, "出張": 0})

    # 月データの解析
    year, month_num = map(int, month.split("-"))

    # カレンダー用のデータ
    cal = calendar.monthcalendar(year, month_num)

    # エントリーデータの集計
    for row in entries:
        date_str = row["work_date"]
        if date_str.startswith(month):
            loc = row["location"]
            day = int(date_str.split("-")[2])
            calendar_dict[day][loc] = calendar_dict[day].get(loc, 0) + 1

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
    entries = read_all_entries()
    detail = {"在宅": [], "出社": [], "出張": []}
    for row in entries:
        if row["work_date"] == day:
            loc = row["location"]
            detail.setdefault(loc, []).append(row["user_name"])
    return detail


def get_user_data(username: str):
    entries = read_all_entries()
    user_entries = [row for row in entries if row["user_name"] == username]
    user_entries.sort(key=lambda x: x["work_date"])
    return user_entries
