"""
カレンダー関連エンドポイント
----------------

カレンダー表示と日別詳細に関連するルートハンドラー
"""

import calendar
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List
import html
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user import user
from ...crud.attendance import attendance
from ...crud.location import location
from ...crud.calendar import calendar_crud
from ...utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ...utils.common import (
    generate_location_badges,
    has_data_for_day,
    generate_location_styles,
)
from ...utils.calendar_utils import (
    parse_month,
    get_prev_month_date,
    get_next_month_date,
    generate_location_data,
)
from ...core.config import logger

router = APIRouter(prefix="/api", tags=["カレンダー"])
templates = Jinja2Templates(directory="src/templates")


def build_calendar_data(db: Session, month: str) -> Dict[str, Any]:
    """
    特定の月のカレンダーデータを構築する

    Args:
        db: データベースセッション
        month: 月文字列 (YYYY-MM)

    Returns:
        Dict[str, Any]: カレンダーデータ
    """
    try:
        # 月を解析
        year, month_num = parse_month(month)
        month_name = f"{year}年{month_num}月"

        # その月のカレンダーを作成
        cal = calendar.monthcalendar(year, month_num)

        # 勤務場所のリストを取得
        location_types = location.get_all_locations(db)

        # 日ごとの勤務場所カウントを初期化
        location_counts = defaultdict(lambda: defaultdict(int))

        # 月の初日と末日を取得
        first_day = date(year, month_num, 1)
        last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

        # この月の全出席レコードを取得
        attendances = calendar_crud.get_month_attendances(
            db, first_day=first_day, last_day=last_day
        )

        # 勤務場所ごとのカウントを集計
        for attendance in attendances:
            day = attendance.date.day
            location_name = attendance.location
            location_counts[day][location_name] += 1

        # 各週と日に出席情報を付与
        weeks = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    # 月の範囲外の日
                    week_data.append({"day": 0, "date": "", "has_data": False})
                else:
                    current_date = date(year, month_num, day)
                    date_str = current_date.strftime("%Y-%m-%d")

                    # この日の出席データをカウント
                    attendance_count = calendar_crud.count_day_attendances(
                        db, target_date=current_date
                    )

                    day_data = {
                        "day": day,
                        "date": date_str,
                        "has_data": attendance_count > 0,
                    }

                    # 各勤務場所のカウントを追加
                    for loc_type in location_types:
                        day_data[loc_type] = location_counts[day].get(loc_type, 0)

                    week_data.append(day_data)
            weeks.append(week_data)

        # 前月と翌月の情報を計算
        prev_month_date = date(year, month_num, 1) - timedelta(days=1)
        prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"

        next_month_date = date(year, month_num, 28)  # 月末を超えても翌月になる
        if next_month_date.month == month_num:  # まだ同じ月の場合は日付を増やす
            next_month_date = next_month_date.replace(
                day=calendar.monthrange(year, month_num)[1]
            ) + timedelta(days=1)
        next_month = f"{next_month_date.year}-{next_month_date.month:02d}"

        # 勤務場所の表示データを生成
        locations = generate_location_data(location_types)

        return {
            "month_name": month_name,
            "weeks": weeks,
            "locations": locations,
            "prev_month": prev_month,
            "next_month": next_month,
        }
    except Exception as e:
        logger.error(f"Error building calendar data: {str(e)}")
        return {"month_name": "", "weeks": [], "locations": []}


@router.get("/calendar", response_class=HTMLResponse)
def get_calendar(
    request: Request, month: Optional[str] = None, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Display calendar for the specified month

    Args:
        request: FastAPI request object
        month: Month in YYYY-MM format (current month if not specified)
        db: Database session

    Returns:
        HTMLResponse: Rendered calendar HTML
    """
    if month is None:
        month = get_current_month_formatted()

    calendar_data = build_calendar_data(db, month)
    context = {
        "request": request,
        "month": calendar_data["month_name"],
        "calendar": calendar_data,
    }
    return templates.TemplateResponse("partials/calendar.html", context)


@router.get("/day/{day}", response_class=HTMLResponse)
def get_day_detail(
    request: Request, day: str, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Display details for the specified day

    Args:
        request: FastAPI request object
        day: Date in YYYY-MM-DD format
        db: Database session

    Returns:
        HTMLResponse: Rendered daily detail HTML
    """
    detail = attendance.get_day_data(db, day=day)

    # Generate badge information for work locations
    location_types = location.get_all_locations(db)
    locations = generate_location_badges(location_types)

    # Check if data exists
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
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Display details for the specified user

    Args:
        request: FastAPI request object
        user_id: User ID
        month: Month in YYYY-MM format (current month if not specified)
        db: Database session

    Returns:
        HTMLResponse: Rendered user detail HTML
    """
    # Escape user_id
    user_id = html.escape(user_id)
    last_viewed_date = get_last_viewed_date(request)

    if month is None:
        month = get_current_month_formatted()

    # Get user name
    user_name = user.get_user_name_by_id(db, user_id=user_id)

    # Get calendar data for the specified month
    calendar_data = build_calendar_data(db, month)

    # Get user data
    user_entries = attendance.get_user_data(db, user_id=user_id)

    # Create a map of dates and work locations for the user
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # Generate style information for work locations
    location_types = location.get_all_locations(db)
    location_styles = generate_location_styles(location_types)

    # 前月と翌月の情報はcalendar_dataから取得可能
    prev_month = calendar_data["prev_month"]
    next_month = calendar_data["next_month"]

    context = {
        "request": request,
        "user_id": user_id,
        "user_name": user_name,
        "entries": user_entries,
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "location_styles": location_styles,
        "prev_month": prev_month,
        "next_month": next_month,
        "last_viewed_date": last_viewed_date,
    }

    return templates.TemplateResponse("partials/user_detail.html", context)
