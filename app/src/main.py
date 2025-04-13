from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import datetime
from typing import Optional
import os
import logging

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from . import csv_store
from .utils.date_utils import (
    format_date,
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)

app = FastAPI(title="Sokora勤務管理アプリ")

# 静的ファイルを /static で配信
app.mount("/static", StaticFiles(directory="src/static"), name="static")

templates = Jinja2Templates(directory="src/templates")


@app.get("/", response_class=HTMLResponse)
def root_page(request: Request) -> HTMLResponse:
    """トップページを表示する

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    today_str = get_today_formatted()
    day_data = csv_store.get_day_data(today_str)
    location_types = csv_store.get_location_types()

    # 勤務場所のスタイル情報を生成
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []
    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "badge": colors[color_index],
            }
        )

    # データがあるかどうかをチェック
    has_data = any(len(users) > 0 for users in day_data.values())

    context = {
        "request": request,
        "default_day": today_str,
        "default_data": day_data,
        "default_locations": locations,
        "default_has_data": has_data,
    }
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
        month = get_current_month_formatted()

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
    location_types = csv_store.get_location_types()

    # 勤務場所のスタイル情報を生成
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    locations = []
    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        locations.append(
            {
                "name": loc_type,
                "badge": colors[color_index],
            }
        )

    # データがあるかどうかをチェック
    has_data = any(len(users) > 0 for users in detail.values())

    context = {
        "request": request,
        "day": day,
        "data": detail,
        "locations": locations,
        "has_data": has_data,
    }
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
    last_viewed_date = get_last_viewed_date(request)

    if month is None:
        month = get_current_month_formatted()

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

    # 勤務場所のスタイル情報を生成
    location_types = csv_store.get_location_types()
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    location_styles = {}
    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        location_styles[loc_type] = (
            f"bg-{colors[color_index]}/10 text-{colors[color_index]}"
        )

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
        "location_styles": location_styles,
        "prev_month": prev_month_str,
        "next_month": next_month_str,
        "last_viewed_date": last_viewed_date,
    }

    return templates.TemplateResponse("partials/user_detail.html", context)


@app.post("/api/csv/import")
async def import_csv(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    """CSVファイルをインポートする

    Args:
        request: FastAPIリクエストオブジェクト
        file: アップロードされたCSVファイル

    Returns:
        HTMLResponse: インポート結果のHTMLレスポンス
    """
    try:
        contents = await file.read()
        csv_store.import_csv_data(contents.decode("utf-8"))

        # 今日のデータを取得してコンテキストを作成
        today_str = get_today_formatted()
        day_data = csv_store.get_day_data(today_str)

        # 勤務場所のスタイル情報を生成
        location_types = csv_store.get_location_types()
        colors = [
            "success",
            "primary",
            "warning",
            "error",
            "info",
            "accent",
            "secondary",
        ]
        locations = []
        for i, loc_type in enumerate(location_types):
            color_index = i % len(colors)
            locations.append(
                {
                    "name": loc_type,
                    "badge": colors[color_index],
                }
            )

        # データがあるかどうかをチェック
        has_data = any(len(users) > 0 for users in day_data.values())

        context = {
            "request": request,
            "day": today_str,
            "data": day_data,
            "locations": locations,
            "has_data": has_data,
            "success_message": "CSVデータが正常にインポートされました。",
        }

        return templates.TemplateResponse("partials/day_detail.html", context)
    except Exception as e:
        logger.error(f"CSVインポートエラー: {str(e)}")
        raise HTTPException(status_code=400, detail=f"CSVインポートエラー: {str(e)}")


@app.get("/api/csv/export")
def export_csv() -> FileResponse:
    """CSVファイルをエクスポートする

    Returns:
        FileResponse: CSVファイルのダウンロードレスポンス
    """
    try:
        csv_path = csv_store.get_csv_file_path()

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

        return FileResponse(
            path=csv_path,
            filename="work_entries.csv",
            media_type="text/csv",
            content_disposition_type="attachment",
        )
    except Exception as e:
        logger.error(f"CSVエクスポートエラー: {str(e)}")
        raise HTTPException(
            status_code=404, detail=f"CSVファイルが見つかりません: {str(e)}"
        )


@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request) -> HTMLResponse:
    """勤怠入力ページを表示する

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # 社員一覧を取得
    users = csv_store.get_all_users()
    context = {"request": request, "users": users}
    return templates.TemplateResponse("attendance.html", context)


@app.post("/api/user/add", response_class=RedirectResponse)
async def add_user(request: Request, username: str = Form(...)) -> RedirectResponse:
    """ユーザーを追加する

    Args:
        request: FastAPIリクエストオブジェクト
        username: 追加するユーザー名

    Returns:
        RedirectResponse: 勤怠入力ページへのリダイレクト
    """
    try:
        success = csv_store.add_user(username)
        if not success:
            raise HTTPException(
                status_code=400, detail=f"ユーザー「{username}」の追加に失敗しました"
            )
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        logger.error(f"ユーザー追加エラー: {str(e)}")
        raise HTTPException(status_code=400, detail=f"ユーザー追加エラー: {str(e)}")


@app.post("/api/user/delete/{username}", response_class=RedirectResponse)
async def delete_user(request: Request, username: str) -> RedirectResponse:
    """ユーザーを削除する

    Args:
        request: FastAPIリクエストオブジェクト
        username: 削除するユーザー名

    Returns:
        RedirectResponse: 勤怠入力ページへのリダイレクト
    """
    try:
        success = csv_store.delete_user(username)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"ユーザー「{username}」が見つかりません"
            )
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        logger.error(f"ユーザー削除エラー: {str(e)}")
        raise HTTPException(status_code=400, detail=f"ユーザー削除エラー: {str(e)}")


@app.get("/attendance/edit/{username}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request, username: str, month: Optional[str] = None
) -> HTMLResponse:
    """ユーザーの勤怠編集ページを表示する

    Args:
        request: FastAPIリクエストオブジェクト
        username: ユーザー名
        month: YYYY-MM形式の月指定（未指定の場合は現在の月）

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    if month is None:
        month = get_current_month_formatted()

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

    # 勤務場所のスタイル情報と選択肢を生成
    location_types = csv_store.get_location_types()
    colors = ["success", "primary", "warning", "error", "info", "accent", "secondary"]
    location_styles = {}
    for i, loc_type in enumerate(location_types):
        color_index = i % len(colors)
        location_styles[loc_type] = (
            f"bg-{colors[color_index]}/10 text-{colors[color_index]}"
        )

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
        "location_styles": location_styles,
        "location_types": location_types,
        "prev_month": prev_month_str,
        "next_month": next_month_str,
        "edit_mode": True,
    }

    return templates.TemplateResponse("attendance_edit.html", context)


@app.post("/api/attendance/update", response_class=RedirectResponse)
async def update_attendance(
    request: Request,
    username: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
) -> RedirectResponse:
    """ユーザーの勤怠情報を更新する

    Args:
        request: FastAPIリクエストオブジェクト
        username: ユーザー名
        date: 更新する日付
        location: 勤務場所

    Returns:
        RedirectResponse: ユーザー編集ページへのリダイレクト
    """
    try:
        success = csv_store.update_user_entry(username, date, location)
        if not success:
            raise HTTPException(status_code=400, detail=f"勤怠情報の更新に失敗しました")
        # 更新後は同じユーザーの編集ページにリダイレクト
        month = "-".join(date.split("-")[:2])  # YYYY-MM-DD から YYYY-MM を取得
        return RedirectResponse(
            url=f"/attendance/edit/{username}?month={month}", status_code=303
        )
    except Exception as e:
        logger.error(f"勤怠更新エラー: {str(e)}")
        raise HTTPException(status_code=400, detail=f"勤怠更新エラー: {str(e)}")
