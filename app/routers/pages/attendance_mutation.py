"""勤怠modalからのHTMX writeをHTML/page adapterとして扱う。"""

from datetime import date as Date
from datetime import timedelta
from typing import Optional, cast

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services import attendance_service
from app.services.errors import ApplicationError

from .responses import hx_error_response, hx_trigger_response

router = APIRouter(prefix="/attendance/entries", tags=["Pages"])


def _refresh_response(*, user_id: str, attendance_date: Date) -> Response:
    """変更対象日から月/週を決め、既存のHTMX refresh contractを返す。

    Args:
        user_id: 変更対象user ID。
        attendance_date: 変更対象日。

    Returns:
        modal closeと月次/週次refresh eventを含むHTMX response。
    """
    month = attendance_date.strftime("%Y-%m")
    monday = attendance_date - timedelta(days=attendance_date.weekday())
    week = monday.isoformat()
    return hx_trigger_response(
        {
            "closeModal": f"attendance-modal-{user_id}-{attendance_date.isoformat()}",
            "refreshUserAttendance": {
                "user_id": user_id,
                "month": month,
                "week": week,
            },
            "refreshAttendance": {"month": month, "week": week},
        }
    )


def _error_response(exc: ApplicationError) -> HTMLResponse:
    """application errorをattendance modal内のHTMX error responseへ変換する。

    Args:
        exc: service layerのapplication error。

    Returns:
        attendance form error targetへ差し替えるHTML response。
    """
    return hx_error_response(exc.detail, target="#attendance-form-error")


@router.post("")
def create_attendance(
    user_id: str = Form(...),
    date: Date = Form(...),
    location_id: int = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> Response:
    """attendance modalのform入力から勤怠を作成する。

    Args:
        user_id: 対象user ID。
        date: 対象日。
        location_id: 登録する勤怠種別ID。
        note: optional note。
        db: DB session。

    Returns:
        成功時はmodal close/refresh event response。application validation failure時はmodal内error HTML。
    """
    try:
        created = attendance_service.create_attendance(
            db,
            attendance_in=AttendanceCreate(
                user_id=user_id,
                date=date,
                location_id=location_id,
                note=note,
            ),
        )
    except ApplicationError as exc:
        return _error_response(exc)
    return _refresh_response(
        user_id=str(created.user_id),
        attendance_date=cast(Date, created.date),
    )


@router.put("/{attendance_id}")
def update_attendance(
    attendance_id: int,
    location_id: int = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> Response:
    """attendance modalのform入力から勤怠を更新する。

    Args:
        attendance_id: 更新対象の勤怠ID。
        location_id: 更新後の勤怠種別ID。
        note: optional note。
        db: DB session。

    Returns:
        成功時はmodal close/refresh event response。application validation failure時はmodal内error HTML。
    """
    try:
        updated = attendance_service.update_attendance(
            db,
            attendance_id=attendance_id,
            attendance_in=AttendanceUpdate(location_id=location_id, note=note),
        )
    except ApplicationError as exc:
        return _error_response(exc)
    return _refresh_response(
        user_id=str(updated.user_id),
        attendance_date=cast(Date, updated.date),
    )


@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """attendance modalから勤怠を削除する。

    Args:
        attendance_id: 削除対象の勤怠ID。
        db: DB session。

    Returns:
        成功時はmodal close/refresh event response。application validation failure時はmodal内error HTML。
    """
    try:
        deleted = attendance_service.delete_attendance(
            db,
            attendance_id=attendance_id,
        )
    except ApplicationError as exc:
        return _error_response(exc)
    return _refresh_response(
        user_id=str(deleted.user_id),
        attendance_date=cast(Date, deleted.date),
    )
