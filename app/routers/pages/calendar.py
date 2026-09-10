"""カレンダー表示のpage/HTMX adapter。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import logger
from app.db.session import get_db
from app.services import calendar_read_service
from app.utils.calendar_utils import (
    get_current_month_formatted,
    parse_date,
    parse_month,
)

router = APIRouter(prefix="/calendar", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_calendar(
    request: Request,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """月次summary calendarをrenderする。

    HTTP month validationだけをこのadapterで処理し、read service内部のValueError等を
    validation errorへ誤変換しない。
    """
    current_month = month or get_current_month_formatted()
    try:
        year, month_num = parse_month(current_month)
        current_month = f"{year}-{month_num:02d}"
    except ValueError as exc:
        logger.warning("無効なcalendar month '%s': %s", month, exc)
        fallback_month = get_current_month_formatted()
        return RedirectResponse(url=f"/calendar?month={fallback_month}")

    view_model = calendar_read_service.get_month_view_model(
        db,
        month=current_month,
    )

    return templates.TemplateResponse(
        "components/top/summary_calendar.html",
        {"request": request, **view_model},
    )


@router.get("/day/{day}", response_class=HTMLResponse)
def get_day_detail(
    request: Request,
    day: str,
    db: Session = Depends(get_db),
) -> Any:
    """日別calendar detailをrenderする。"""
    target_date = parse_date(day)
    if target_date is None:
        return HTMLResponse(
            content="無効な日付です。",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    view_model = calendar_read_service.get_day_detail_view_model(
        db,
        day=target_date,
    )
    return templates.TemplateResponse(
        "components/top/day_detail.html",
        {"request": request, **view_model},
    )
