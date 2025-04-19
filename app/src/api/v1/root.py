"""
ルートページ表示
----------------

メインページ表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...services import csv_store
from ...utils.date_utils import get_today_formatted
from ...utils.common import generate_location_badges, has_data_for_day

router = APIRouter(tags=["ページ表示"])
templates = Jinja2Templates(directory="src/templates")


@router.get("/", response_class=HTMLResponse)
def root_page(request: Request) -> HTMLResponse:
    """Display the top page

    Args:
        request: FastAPI request object

    Returns:
        HTMLResponse: Rendered HTML page
    """
    today_str = get_today_formatted()
    day_data = csv_store.get_day_data(today_str)

    # Get types of work locations
    location_types = csv_store.get_location_types()

    # Generate badge information for work locations
    locations = generate_location_badges(location_types)

    # Check if data exists
    has_data = has_data_for_day(day_data)

    context = {
        "request": request,
        "default_day": today_str,
        "default_data": day_data,
        "default_locations": locations,
        "default_has_data": has_data,
    }
    return templates.TemplateResponse("base.html", context)
