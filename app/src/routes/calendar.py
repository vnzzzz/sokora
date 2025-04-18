"""
Calendar-Related Endpoints
----------------

Route handlers related to calendar display and daily details
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

router = APIRouter(prefix="/api", tags=["Calendar"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/calendar", response_class=HTMLResponse)
def get_calendar(request: Request, month: Optional[str] = None) -> HTMLResponse:
    """Display calendar for the specified month

    Args:
        request: FastAPI request object
        month: Month in YYYY-MM format (current month if not specified)

    Returns:
        HTMLResponse: Rendered calendar HTML
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
    """Display details for the specified day

    Args:
        request: FastAPI request object
        day: Date in YYYY-MM-DD format

    Returns:
        HTMLResponse: Rendered daily detail HTML
    """
    detail = csv_store.get_day_data(day)

    # Generate badge information for work locations
    location_types = csv_store.get_location_types()
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
    request: Request, user_id: str, month: Optional[str] = None
) -> HTMLResponse:
    """Display details for the specified user

    Args:
        request: FastAPI request object
        user_id: User ID
        month: Month in YYYY-MM format (current month if not specified)

    Returns:
        HTMLResponse: Rendered user detail HTML
    """
    # Escape user_id
    user_id = html.escape(user_id)
    last_viewed_date = get_last_viewed_date(request)

    if month is None:
        month = get_current_month_formatted()

    # Get user name
    user_name = csv_store.get_user_name_by_id(user_id)

    # Get calendar data for the specified month
    calendar_data = csv_store.get_calendar_data(month)

    # Get user data
    user_entries = csv_store.get_user_data(user_id)

    # Create a map of dates and work locations for the user
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # Generate style information for work locations
    location_types = csv_store.get_location_types()
    location_styles = generate_location_styles(location_types)

    # Set up previous and next month (using functions from utils/calendar_utils)
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
