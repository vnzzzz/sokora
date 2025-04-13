"""
カレンダー関連のエンドポイント
----------------

カレンダー表示や日別詳細に関連するルートハンドラー
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from .. import csv_store
from ..utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ..utils.common import (
    generate_location_badges,
    has_data_for_day,
    generate_location_styles,
)

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")


@router.get("/api/calendar", response_class=HTMLResponse)
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


@router.get("/api/day/{day}", response_class=HTMLResponse)
def get_day_detail(request: Request, day: str) -> HTMLResponse:
    """指定された日の詳細を表示する

    Args:
        request: FastAPIリクエストオブジェクト
        day: YYYY-MM-DD形式の日付

    Returns:
        HTMLResponse: レンダリングされた日別詳細HTML
    """
    detail = csv_store.get_day_data(day)

    # 勤務場所のバッジ情報を生成
    locations = generate_location_badges()

    # データがあるかどうかをチェック
    has_data = has_data_for_day(detail)

    context = {
        "request": request,
        "day": day,
        "data": detail,
        "locations": locations,
        "has_data": has_data,
    }
    return templates.TemplateResponse("partials/day_detail.html", context)


@router.get("/api/user/{username}", response_class=HTMLResponse)
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
    location_styles = generate_location_styles()

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
