from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import datetime
from typing import Optional, Dict, Any

from . import csv_store

app = FastAPI()

# 静的ファイルを /static で配信
app.mount("/static", StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory="src/templates")


def format_date(date: datetime.date) -> str:
    """日付をYYYY-MM-DD形式に整形する

    Args:
        date: 日付オブジェクト

    Returns:
        str: YYYY-MM-DD形式の文字列
    """
    return f"{date.year}-{date.month:02d}-{date.day:02d}"


@app.get("/", response_class=HTMLResponse)
def root_page(request: Request) -> HTMLResponse:
    """トップページを表示する

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # デフォルトで今日のデータを取得
    today = datetime.date.today()
    today_str = format_date(today)
    day_data = csv_store.get_day_data(today_str)

    context = {"request": request, "default_day": today_str, "default_data": day_data}
    return templates.TemplateResponse("base.html", context)


@app.get("/api/calendar", response_class=HTMLResponse)
def get_calendar(request: Request, month: Optional[str] = None) -> HTMLResponse:
    """指定された月のカレンダーを表示する

    Args:
        request: FastAPIリクエストオブジェクト
        month: YYYY-MM形式の月指定（未指定の場合は現在の月）

    Returns:
        HTMLResponse: レンダリングされたカレンダーHTML
    """
    if month is None:
        # デフォルトで今月を表示
        today = datetime.date.today()
        month = f"{today.year}-{today.month:02d}"

    calendar_data = csv_store.get_calendar_data(month)
    context = {
        "request": request,
        "month": calendar_data["month_name"],
        "calendar": calendar_data,
    }
    return templates.TemplateResponse("partials/calendar.html", context)


@app.get("/api/day/{day}", response_class=HTMLResponse)
def get_day_detail(request: Request, day: str) -> HTMLResponse:
    """指定された日の詳細を表示する

    Args:
        request: FastAPIリクエストオブジェクト
        day: YYYY-MM-DD形式の日付

    Returns:
        HTMLResponse: レンダリングされた日別詳細HTML
    """
    detail = csv_store.get_day_data(day)
    context = {"request": request, "day": day, "data": detail}
    return templates.TemplateResponse("partials/day_detail.html", context)


@app.get("/api/user/{username}", response_class=HTMLResponse)
def get_user_detail(
    request: Request, username: str, month: Optional[str] = None
) -> HTMLResponse:
    """指定されたユーザーの詳細を表示する

    Args:
        request: FastAPIリクエストオブジェクト
        username: ユーザー名
        month: YYYY-MM形式の月指定（未指定の場合は現在の月）

    Returns:
        HTMLResponse: レンダリングされたユーザー詳細HTML
    """
    # 最後に表示していた日付を取得 (リファラーから)
    referer = request.headers.get("referer", "")
    last_viewed_date = ""
    if "/api/day/" in referer:
        last_viewed_date = referer.split("/api/day/")[-1].split("?")[0]
    else:
        # デフォルトは今日
        today = datetime.date.today()
        last_viewed_date = format_date(today)

    if month is None:
        # デフォルトで今月を表示
        today = datetime.date.today()
        month = f"{today.year}-{today.month:02d}"

    # 指定された月のカレンダーデータを取得
    calendar_data = csv_store.get_calendar_data(month)

    # ユーザーのデータを取得
    user_entries = csv_store.get_user_data(username)

    # ユーザーの予定がある日付と勤務場所のマップを作成
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # 前月と次月の設定
    year, month_num = map(int, month.split("-"))
    prev_month = csv_store.get_prev_month_date(year, month_num)
    prev_month_str = f"{prev_month.year}-{prev_month.month:02d}"
    next_month = csv_store.get_next_month_date(year, month_num)
    next_month_str = f"{next_month.year}-{next_month.month:02d}"

    context = {
        "request": request,
        "username": username,
        "entries": user_entries,
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "prev_month": prev_month_str,
        "next_month": next_month_str,
        "last_viewed_date": last_viewed_date,
    }

    return templates.TemplateResponse("partials/user_detail.html", context)


@app.post("/api/csv/import")
async def import_csv(file: UploadFile = File(...)) -> Dict[str, str]:
    """CSVファイルをインポートする

    Args:
        file: アップロードされたCSVファイル

    Returns:
        Dict[str, str]: インポート結果のステータス
    """
    contents = await file.read()
    csv_store.import_csv_data(contents.decode("utf-8"))
    return {"status": "ok", "message": "CSV imported successfully"}


@app.get("/api/csv/export")
def export_csv() -> FileResponse:
    """CSVファイルをエクスポートする

    Returns:
        FileResponse: CSVファイルのダウンロードレスポンス
    """
    csv_path = Path("work_entries.csv")
    return FileResponse(csv_path, media_type="text/csv", filename="work_entries.csv")
