"""勤怠のJSON API endpoint。"""

from datetime import date as Date
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_db
from app.schemas.attendance import (
    Attendance,
    AttendanceCreate,
    AttendanceList,
    AttendanceUpdate,
)
from app.services import attendance_service

router = APIRouter(tags=["Attendance"])


@router.get("", response_model=AttendanceList)
def get_attendances(db: Session = Depends(get_db)) -> Any:
    """全勤怠レコードをJSON APIのrecords形式で返す。"""
    return {"records": crud.attendance.list_all(db)}


@router.get("/day/{day}")
def get_day_attendance(day: str, db: Session = Depends(get_db)) -> Any:
    """YYYY-MM-DDの日別勤怠projectionをJSONで返す。"""
    return {"success": True, "data": crud.attendance.get_day_data(db, day=day)}


@router.post(
    "",
    response_model=Attendance,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance(
    attendance_in: AttendanceCreate,
    db: Session = Depends(get_db),
) -> Attendance:
    """JSON bodyから勤怠を作成する。"""
    return attendance_service.create_attendance(db, attendance_in=attendance_in)


@router.put("/{attendance_id}", response_model=Attendance)
def update_attendance(
    attendance_id: int,
    attendance_in: AttendanceUpdate,
    db: Session = Depends(get_db),
) -> Attendance:
    """JSON bodyから勤怠を更新する。"""
    return attendance_service.update_attendance(
        db,
        attendance_id=attendance_id,
        attendance_in=attendance_in,
    )


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """勤怠IDで1件削除する。"""
    attendance_service.delete_attendance(db, attendance_id=attendance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_by_user_date(
    user_id: str,
    date: Date,
    db: Session = Depends(get_db),
) -> Response:
    """ユーザーと日付で勤怠を削除する。"""
    attendance_service.delete_attendance_by_user_date(
        db,
        user_id=user_id,
        attendance_date=date,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
