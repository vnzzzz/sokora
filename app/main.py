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
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


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
def get_user_detail(request: Request, username: str) -> HTMLResponse:
    """指定されたユーザーの詳細を表示する

    Args:
        request: FastAPIリクエストオブジェクト
        username: ユーザー名

    Returns:
        HTMLResponse: レンダリングされたユーザー詳細HTML
    """
    user_entries = csv_store.get_user_data(username)
    context = {"request": request, "username": username, "entries": user_entries}
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
