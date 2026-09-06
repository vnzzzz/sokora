"""カレンダー表示のpage/HTMX adapter。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import get_db
from app.services import calendar_read_service
from app.utils.calendar_utils import get_current_month_formatted

router = APIRouter(prefix="/calendar", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_calendar(
    request: Request,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """月次summary calendarをrenderする。"""
    try:
        view_model = calendar_read_service.get_month_view_model(db, month=month)
    except ValueError as exc:
        logger.warning("無効なcalendar month '%s': %s", month, exc)
        current_month = get_current_month_formatted()
        return RedirectResponse(url=f"/calendar?month={current_month}")

    headers = (
        {"HX-Reswap": "innerHTML"}
        if request.headers.get("HX-Request") == "true"
        else {}
    )
    return templates.TemplateResponse(
        "components/top/summary_calendar.html",
        {"request": request, **view_model},
        headers=headers,
    )


@router.get("/day/{day}", response_class=HTMLResponse)
def get_day_detail(
    request: Request,
    day: str,
    db: Session = Depends(get_db),
) -> Any:
    """日別calendar detailをrenderする。"""
    view_model = calendar_read_service.get_day_detail_view_model(db, day=day)
    return templates.TemplateResponse(
        "components/top/day_detail.html",
        {"request": request, **view_model},
    )
