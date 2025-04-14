"""
Attendance-Related Endpoints
----------------

Route handlers related to attendance input and editing
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

# Router for API
router = APIRouter(prefix="/api", tags=["Attendance Management"])
# Router for HTML display
page_router = APIRouter(tags=["Page Display"])
templates = Jinja2Templates(directory="src/templates")


@page_router.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request) -> HTMLResponse:
    """Display the attendance management page

    Args:
        request: FastAPI request object

    Returns:
        HTMLResponse: Rendered HTML page
    """
    users = csv_store.get_all_users()
    return templates.TemplateResponse(
        "attendance.html", {"request": request, "users": users}
    )


@page_router.get("/attendance/edit/{user_id}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request, user_id: str, month: Optional[str] = None
) -> HTMLResponse:
    """Display page to edit user attendance

    Args:
        request: FastAPI request object
        user_id: User ID to edit
        month: Month in YYYY-MM format (current month if not specified)

    Returns:
        HTMLResponse: Rendered HTML page
    """
    if month is None:
        month = get_current_month_formatted()

    # Get calendar data for the specified month
    calendar_data = csv_store.get_calendar_data(month)

    # Get user name
    user_name = csv_store.get_user_name_by_id(user_id)

    # Get user data
    user_entries = csv_store.get_user_data(user_id)
    all_users = csv_store.get_all_users()
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
    location_types = csv_store.get_location_types()

    # Generate style information for work locations
    location_styles = generate_location_styles(location_types)

    # Set up previous and next month
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
    request: Request, username: str = Form(...), user_id: str = Form(...)
) -> RedirectResponse:
    """Add a new user

    Args:
        request: FastAPI request object
        username: Username to add (form data)
        user_id: User ID (form data)

    Returns:
        RedirectResponse: Redirect to attendance page
    """
    try:
        csv_store.add_user(username, user_id)
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/delete/{user_id}", response_class=RedirectResponse)
async def delete_user(request: Request, user_id: str) -> RedirectResponse:
    """Delete a user

    Args:
        request: FastAPI request object
        user_id: User ID to delete

    Returns:
        RedirectResponse: Redirect to attendance page
    """
    try:
        csv_store.delete_user(user_id)
        return RedirectResponse(url="/attendance", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attendance/update", response_class=RedirectResponse)
async def update_attendance(
    request: Request,
    user_id: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
) -> RedirectResponse:
    """Update a user's work location

    Args:
        request: FastAPI request object
        user_id: User ID to update (form data)
        date: Date to update (form data)
        location: Work location to update (form data)

    Returns:
        RedirectResponse: Redirect to user edit page
    """
    try:
        csv_store.update_user_entry(user_id, date, location)
        return RedirectResponse(url=f"/attendance/edit/{user_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
