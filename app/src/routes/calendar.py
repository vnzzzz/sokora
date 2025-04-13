"""
カレンダー関連のエンドポイント
----------------

カレンダー表示や日別詳細に関連するルートハンドラー
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import html

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

router = APIRouter(prefix="/api", tags=["カレンダー"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/calendar", response_class=HTMLResponse)
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


@router.get("/day/{day}", response_class=HTMLResponse)
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
    location_types = csv_store.get_location_types()
    locations = generate_location_badges(location_types)

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


@router.get("/user/{user_id}", response_class=HTMLResponse)
def get_user_detail(
    request: Request, user_id: str, month: Optional[str] = None
) -> HTMLResponse:
    """指定されたユーザーの詳細を表示する

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: ユーザーID
        month: YYYY-MM形式の月指定（未指定の場合は現在の月）

    Returns:
        HTMLResponse: レンダリングされたユーザー詳細HTML
    """
    # user_idをエスケープ処理
    user_id = html.escape(user_id)
    last_viewed_date = get_last_viewed_date(request)

    if month is None:
        month = get_current_month_formatted()

    # ユーザー名の取得
    user_name = csv_store.get_user_name_by_id(user_id)

    # 指定された月のカレンダーデータを取得
    calendar_data = csv_store.get_calendar_data(month)

    # ユーザーのデータを取得
    user_entries = csv_store.get_user_data(user_id)

    # ユーザーの予定がある日付と勤務場所のマップを作成
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # 勤務場所のスタイル情報を生成
    location_types = csv_store.get_location_types()
    location_styles = generate_location_styles(location_types)

    # 前月と次月の設定（utils/calendar_utils の関数を使用）
    from ..utils.calendar_utils import (
        parse_month,
        get_prev_month_date,
        get_next_month_date,
    )

    year, month_num = parse_month(month)
    prev_month = get_prev_month_date(year, month_num)
    prev_month_str = f"{prev_month.year}-{prev_month.month:02d}"
    next_month = get_next_month_date(year, month_num)
    next_month_str = f"{next_month.year}-{next_month.month:02d}"

    context = {
        "request": request,
        "user_id": user_id,
        "user_name": user_name,
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
