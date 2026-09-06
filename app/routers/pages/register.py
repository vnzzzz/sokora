"""勤怠monthly page/HTMX adapter。"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import attendance_read_service
from app.utils.calendar_utils import get_current_month_formatted, parse_month

router = APIRouter(prefix="/attendance/monthly", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def _normalize_month_or_redirect(
    month: Optional[str],
) -> tuple[str, RedirectResponse | None]:
    """monthly top page用にmonthを正規化し、不正値はcurrent monthへredirectする。"""
    if month is None:
        return get_current_month_formatted(), None

    try:
        year, month_num = parse_month(month)
    except ValueError as exc:
        logger.warning("無効な月パラメータ '%s': %s", month, exc)
        current_month = get_current_month_formatted()
        return current_month, RedirectResponse(
            url=f"/attendance/monthly?month={current_month}"
        )
    return f"{year}-{month_num:02d}", None


@router.get("", response_class=HTMLResponse)
def register_page(
    request: Request,
    search_query: Optional[str] = None,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """monthly register user listをrenderする。"""
    current_month, redirect = _normalize_month_or_redirect(month)
    if redirect is not None:
        return redirect

    view_model = attendance_read_service.get_monthly_register_page_view_model(
        db,
        month=current_month,
        search_query=search_query,
    )
    context = {"request": request, **view_model}

    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            "components/partials/register/user_list.html",
            context,
            headers={"HX-Reswap": "outerHTML"},
        )
    return templates.TemplateResponse("pages/register.html", context)


@router.get("/users/{user_id}", response_class=HTMLResponse)
def user_calendar(
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """特定userのmonthly calendar partialをrenderする。"""
    if month is None:
        current_month = get_current_month_formatted()
    else:
        try:
            year, month_num = parse_month(month)
            current_month = f"{year}-{month_num:02d}"
        except ValueError as exc:
            logger.warning(
                "無効な個別calendar月パラメータ '%s': %s",
                month,
                exc,
            )
            current_month = get_current_month_formatted()
            return RedirectResponse(
                url=f"/attendance/monthly/users/{user_id}?month={current_month}"
            )

    view_model = attendance_read_service.get_user_monthly_calendar_view_model(
        db,
        user_id=user_id,
        month=current_month,
    )
    if view_model is None:
        logger.warning("ユーザーが見つかりません: %s", user_id)
        return HTMLResponse(content="ユーザーが見つかりません。", status_code=404)

    return templates.TemplateResponse(
        "components/partials/register/user_calendar.html",
        {"request": request, **view_model},
        headers={"HX-Reswap": "outerHTML"}
        if request.headers.get("HX-Request") == "true"
        else {},
    )
