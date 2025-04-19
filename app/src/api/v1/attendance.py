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
from ...services import db_service
from ...utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ...utils.common import generate_location_styles

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
    users = db_service.get_all_users(db)
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
    calendar_data = db_service.get_calendar_data(db, month)

    # Get user name
    user_name = db_service.get_user_name_by_id(db, user_id)

    # Get user data
    user_entries = db_service.get_user_data(db, user_id)
    all_users = db_service.get_all_users(db)
    all_user_ids = [user[1] for user in all_users]

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
    location_types = db_service.get_location_types(db)

    # Generate style information for work locations
    location_styles = generate_location_styles(location_types)

    # Set up previous and next month
    from ...utils.calendar_utils import (
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
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "location_styles": location_styles,
        "location_types": location_types,
        "prev_month": prev_month_str,
        "next_month": next_month_str,
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
        db_service.add_user(db, username, user_id)
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
        db_service.delete_user(db, user_id)
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
        db_service.update_user_entry(db, user_id, date, location)
        return RedirectResponse(url=f"/attendance/edit/{user_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
