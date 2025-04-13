"""
勤怠関連のエンドポイント
----------------

勤怠入力や編集に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from .. import csv_store
from ..utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ..utils.common import generate_location_styles

# API用ルーター
router = APIRouter(prefix="/api", tags=["勤怠管理"])
# HTML表示用ルーター
page_router = APIRouter(tags=["ページ表示"])
templates = Jinja2Templates(directory="src/templates")


@page_router.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request) -> HTMLResponse:
    """勤怠入力ページを表示する

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    users = csv_store.get_all_users()
    return templates.TemplateResponse(
        "attendance.html", {"request": request, "users": users}
    )


@page_router.get("/attendance/edit/{username}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request, username: str, month: Optional[str] = None
) -> HTMLResponse:
    """ユーザーの勤怠を編集するページを表示する

    Args:
        request: FastAPIリクエストオブジェクト
        username: 編集するユーザー名
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
    if not user_entries and not csv_store.get_all_users().count(username):
        raise HTTPException(
            status_code=404, detail=f"ユーザー '{username}' が見つかりません"
        )

    # ユーザーの予定がある日付と勤務場所のマップを作成
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # 勤務場所のスタイル情報を生成
    location_styles = generate_location_styles()
    location_types = csv_store.get_location_types()

    # 前月と次月の設定
    year, month_num = map(int, month.split("-"))
    prev_month = csv_store.get_prev_month_date(year, month_num)
    prev_month_str = f"{prev_month.year}-{prev_month.month:02d}"
    next_month = csv_store.get_next_month_date(year, month_num)
    next_month_str = f"{next_month.year}-{next_month.month:02d}"

    context = {
        "request": request,
        "username": username,
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "location_styles": location_styles,
        "location_types": location_types,
        "prev_month": prev_month_str,
        "next_month": next_month_str,
    }

    return templates.TemplateResponse("attendance_edit.html", context)


# APIエンドポイント
@router.post("/user/add", response_class=RedirectResponse)
async def add_user(request: Request, username: str = Form(...)) -> RedirectResponse:
    """新しいユーザーを追加する

    Args:
        request: FastAPIリクエストオブジェクト
        username: 追加するユーザー名（フォームデータ）

    Returns:
        RedirectResponse: 勤怠入力ページへのリダイレクト
    """
    try:
        csv_store.add_user(username)
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/delete/{username}", response_class=RedirectResponse)
async def delete_user(request: Request, username: str) -> RedirectResponse:
    """ユーザーを削除する

    Args:
        request: FastAPIリクエストオブジェクト
        username: 削除するユーザー名

    Returns:
        RedirectResponse: 勤怠入力ページへのリダイレクト
    """
    try:
        csv_store.delete_user(username)
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attendance/update", response_class=RedirectResponse)
async def update_attendance(
    request: Request,
    username: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
) -> RedirectResponse:
    """ユーザーの勤務場所を更新する

    Args:
        request: FastAPIリクエストオブジェクト
        username: 更新するユーザー名（フォームデータ）
        date: 更新する日付（フォームデータ）
        location: 更新する勤務場所（フォームデータ）

    Returns:
        RedirectResponse: ユーザー編集ページへのリダイレクト
    """
    try:
        csv_store.update_user_entry(username, date, location)
        return RedirectResponse(url=f"/attendance/edit/{username}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
