"""勤怠入力と編集に関連するAPIエンドポイント。"""

import json
import re
from datetime import date as Date
from datetime import datetime, timedelta
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import logger
from app.crud.attendance import attendance
from app.db.session import get_db
from app.schemas.attendance import AttendanceList
from app.services import attendance_service

router = APIRouter(tags=["Attendance"])


@router.get("", response_model=AttendanceList)
def get_attendances(db: Session = Depends(get_db)) -> Any:
    """全勤怠レコードをAPIのrecords形式で返します。"""
    attendances = db.query(attendance.model).all()
    return {"records": attendances}


@router.get("/day/{day}")
def get_day_attendance(day: str, db: Session = Depends(get_db)) -> Any:
    """YYYY-MM-DDの日付文字列を受け取り、その日の勤怠表示データを返します。"""
    detail = attendance.get_day_data(db, day=day)
    if not detail:
        return {"success": True, "data": {}}
    return {"success": True, "data": detail}


def extract_month_from_request(request: Request) -> Optional[str]:
    """HTMX更新後も表示中の月を維持するため、RefererからYYYY-MMを取得します。

    テスト時はx-test-month headerをfallbackとして使用し、取得不能時はNoneを返します。
    """
    referer = request.headers.get("referer", "")
    month_match = re.search(r"month=([0-9]{4}-[0-9]{2})", referer)
    if month_match:
        return month_match.group(1)
    if "x-test-month" in request.headers:
        return request.headers.get("x-test-month")
    return None


def extract_week_from_request(
    request: Request, attendance_date: Optional[Date] = None
) -> Optional[str]:
    """HTMX更新後も表示中の週を維持するため、週の月曜日をYYYY-MM-DDで返します。

    Referer、テスト用header、勤怠日の順でfallbackし、特定できなければNoneを返します。
    """
    referer = request.headers.get("referer", "")
    week_match = re.search(r"week=([0-9]{4}-[0-9]{2}-[0-9]{2})", referer)
    if week_match:
        return week_match.group(1)
    if "x-test-week" in request.headers:
        return request.headers.get("x-test-week")
    if attendance_date:
        monday = attendance_date - timedelta(days=attendance_date.weekday())
        return monday.isoformat()
    return None


def _trigger_response(
    request: Request,
    *,
    user_id: str,
    attendance_date: Date,
) -> Response:
    """勤怠modalを閉じ、現在の月・週表示を再読込するHX-Trigger付き204を返します。"""
    current_month = extract_month_from_request(request)
    current_week = extract_week_from_request(request, attendance_date)
    trigger_data = {
        "closeModal": f"attendance-modal-{user_id}-{attendance_date.isoformat()}",
        "refreshUserAttendance": {
            "user_id": user_id,
            "month": current_month,
            "week": current_week,
        },
        "refreshAttendance": {
            "month": current_month,
            "week": current_week,
        },
    }
    return Response(
        content="",
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"HX-Trigger": json.dumps(trigger_data)},
    )


@router.post("", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def create_attendance(
    request: Request,
    user_id: str = Form(...),
    date_str: str = Form(..., alias="date"),
    location_id: int = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> Response:
    """form入力から勤怠を作成し、成功時はHTMX更新trigger付き204を返します。"""
    try:
        attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="日付の形式が無効です。YYYY-MM-DD形式で入力してください。",
        )

    created = attendance_service.create_attendance(
        db,
        user_id=user_id,
        attendance_date=attendance_date,
        location_id=location_id,
        note=note,
    )
    logger.debug("勤怠ID %s の作成に成功しました", created.id)
    return _trigger_response(
        request,
        user_id=str(created.user_id),
        attendance_date=cast(Date, created.date),
    )


@router.put(
    "/{attendance_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT
)
async def update_attendance(
    request: Request,
    attendance_id: int,
    location_id: int = Form(...),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> Response:
    """勤怠IDの勤務地・備考を更新し、成功時はHTMX更新trigger付き204を返します。"""
    updated = attendance_service.update_attendance(
        db,
        attendance_id=attendance_id,
        location_id=location_id,
        note=note,
    )
    logger.debug("勤怠ID %s の更新に成功しました", attendance_id)
    return _trigger_response(
        request,
        user_id=str(updated.user_id),
        attendance_date=cast(Date, updated.date),
    )


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attendance(
    request: Request,
    attendance_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """勤怠IDで1件削除し、成功時はHTMX更新trigger付き204を返します。"""
    deleted = attendance_service.delete_attendance(db, attendance_id=attendance_id)
    return _trigger_response(
        request,
        user_id=str(deleted.user_id),
        attendance_date=cast(Date, deleted.date),
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_by_user_date(
    request: Request,
    user_id: str,
    date: Date,
    db: Session = Depends(get_db),
) -> Response:
    """ユーザーと日付で勤怠を削除し、成功時はHTMX更新trigger付き204を返します。"""
    deleted = attendance_service.delete_attendance_by_user_date(
        db,
        user_id=user_id,
        attendance_date=date,
    )
    return _trigger_response(
        request,
        user_id=str(deleted.user_id),
        attendance_date=cast(Date, deleted.date),
    )
