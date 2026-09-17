"""勤怠weekly page/HTMX adapter。"""

import json
import logging
from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.attendance import attendance
from app.crud.location import location as location_crud
from app.crud.user import user
from app.db.session import get_db
from app.models.attendance import Attendance as AttendanceModel
from app.models.location import Location
from app.services import attendance_read_service
from app.utils.calendar_utils import (
    format_date_jp,
    get_current_week_formatted,
    parse_week,
)

router = APIRouter(prefix="/attendance", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/weekly", response_class=HTMLResponse)
def attendance_page(
    request: Request,
    search_query: Optional[str] = None,
    week: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """weekly attendance matrixをrenderする。"""
    if week is None:
        week = get_current_week_formatted()
    else:
        try:
            week = parse_week(week).isoformat()
        except ValueError as exc:
            logger.warning("無効な週パラメータ '%s': %s", week, exc)
            current_week = get_current_week_formatted()
            return RedirectResponse(url=f"/attendance/weekly?week={current_week}")

    view_model = attendance_read_service.get_weekly_page_view_model(
        db,
        week=week,
        search_query=search_query,
    )
    context = {"request": request, **view_model}

    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            "components/partials/attendance/calendar.html",
            context,
            headers={"HX-Reswap": "outerHTML"},
        )
    return templates.TemplateResponse("pages/attendance.html", context)


@router.get("/modals/{user_id}/{date_str}", response_class=HTMLResponse)
def get_attendance_modal(
    request: Request,
    user_id: str,
    date_str: str,
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """YYYY-MM-DDの日付を対象に勤怠編集モーダルを返す。"""
    logger.info(
        f"勤怠モーダルリクエスト受信: User={user_id}, Date={date_str}, Mode={mode}"
    )
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        logger.warning(f"無効な日付形式: {date_str}")
        return HTMLResponse(content="", status_code=status.HTTP_400_BAD_REQUEST)

    user_obj = user.get(db, id=user_id)
    if not user_obj:
        logger.warning(f"ユーザーが見つかりません: {user_id}")
        return HTMLResponse(content="", status_code=status.HTTP_404_NOT_FOUND)

    attendance_obj: Optional[AttendanceModel] = attendance.get_by_user_and_date(
        db, user_id=user_id, date=target_date
    )
    attendance_id = attendance_obj.id if attendance_obj else None
    current_location_id = attendance_obj.location_id if attendance_obj else None
    note = attendance_obj.note if attendance_obj else None
    locations: List[Location] = location_crud.list_all(db)

    context = {
        "request": request,
        "attendance_modal_params": {
            "user_id": user_id,
            "date": date_str,
            "user_name": str(user_obj.username),
            "formatted_date": format_date_jp(target_date),
            "attendance_id": attendance_id,
            "current_location_id": current_location_id,
            "locations": locations,
            "mode": mode,
            "note": note,
        },
    }
    logger.debug(f"モーダルコンテキスト: {context}")

    modal_id = f"attendance-modal-{user_id}-{date_str}"
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}

    return templates.TemplateResponse(
        "components/partials/modals/attendance_modal.html", context, headers=headers
    )
