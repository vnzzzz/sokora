"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user import user
from ...crud.attendance import attendance
from ...crud.location import location
from ..v1.calendar import build_calendar_data
from ...utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ...utils.common import generate_location_styles
from ...utils.calendar_utils import (
    parse_month,
    get_prev_month_date,
    get_next_month_date,
)

# API用ルーター
router = APIRouter(prefix="/api", tags=["勤怠管理"])
# ページ表示用ルーター
page_router = APIRouter(tags=["ページ表示"])
templates = Jinja2Templates(directory="src/templates")


@page_router.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Display the attendance management page

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        HTMLResponse: Rendered HTML page
    """
    users = user.get_all_users(db)
    return templates.TemplateResponse(
        "attendance.html", {"request": request, "users": users}
    )


@page_router.get("/attendance/edit/{user_id}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Display page to edit user attendance

    Args:
        request: FastAPI request object
        user_id: User ID to edit
        month: Month in YYYY-MM format (current month if not specified)
        db: Database session

    Returns:
        HTMLResponse: Rendered HTML page
    """
    if month is None:
        month = get_current_month_formatted()

    # Get calendar data for the specified month
    calendar_data = build_calendar_data(db, month)

    # Get user name
    user_name = user.get_user_name_by_id(db, user_id=user_id)

    # Get user data
    user_entries = attendance.get_user_data(db, user_id=user_id)
    all_users = user.get_all_users(db)
    all_user_ids = [user_id for user_name, user_id in all_users]

    if not user_entries and user_id not in all_user_ids:
        raise HTTPException(status_code=404, detail=f"User ID '{user_id}' not found")

    # Create a map of dates and work locations for the user
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # Get types of work locations
    location_types = location.get_all_locations(db)

    # Generate style information for work locations
    location_styles = generate_location_styles(location_types)

    # 前月と翌月の情報はcalendar_dataから取得可能
    prev_month = calendar_data["prev_month"]
    next_month = calendar_data["next_month"]

    context = {
        "request": request,
        "user_id": user_id,
        "user_name": user_name,
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "location_styles": location_styles,
        "location_types": location_types,
        "prev_month": prev_month,
        "next_month": next_month,
        "month_name": calendar_data["month_name"],
    }

    return templates.TemplateResponse("attendance_edit.html", context)


# API endpoints
@router.post("/user/add", response_class=RedirectResponse)
async def add_user(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Add a new user

    Args:
        request: FastAPI request object
        username: Username to add (form data)
        user_id: User ID (form data)
        db: Database session

    Returns:
        RedirectResponse: Redirect to attendance page
    """
    try:
        user.create_user(db, username=username, user_id=user_id)
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/delete/{user_id}", response_class=RedirectResponse)
async def delete_user(
    request: Request, user_id: str, db: Session = Depends(get_db)
) -> RedirectResponse:
    """Delete a user

    Args:
        request: FastAPI request object
        user_id: User ID to delete
        db: Database session

    Returns:
        RedirectResponse: Redirect to attendance page
    """
    try:
        user.delete_user(db, user_id=user_id)
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attendance/update", response_class=RedirectResponse)
async def update_attendance(
    request: Request,
    user_id: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Update a user's work location

    Args:
        request: FastAPI request object
        user_id: User ID to update (form data)
        date: Date to update (form data)
        location: Work location to update (form data)
        db: Database session

    Returns:
        RedirectResponse: Redirect to user edit page
    """
    try:
        attendance.update_user_entry(
            db, user_id=user_id, date_str=date, location=location
        )
        return RedirectResponse(url=f"/attendance/edit/{user_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
