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
    """全勤怠recordをJSON APIのrecords形式で返す。

    Args:
        db: DB session。

    Returns:
        `records`に全勤怠recordを格納したmapping。
    """
    return {"records": crud.attendance.list_all(db)}


@router.get("/day/{day}")
def get_day_attendance(day: Date, db: Session = Depends(get_db)) -> Any:
    """指定日の日別勤怠projectionを返す。

    Args:
        day: 取得対象日。
        db: DB session。

    Returns:
        `success`と日別勤怠projectionを含むmapping。
    """
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
    """JSON bodyから勤怠を作成する。

    Args:
        attendance_in: 作成する勤怠データ。
        db: DB session。

    Returns:
        作成後の勤怠record。

    Raises:
        HTTPException: user/locationが不正、または同一user/dateが重複する場合。
    """
    return attendance_service.create_attendance(db, attendance_in=attendance_in)


@router.put("/{attendance_id}", response_model=Attendance)
def update_attendance(
    attendance_id: int,
    attendance_in: AttendanceUpdate,
    db: Session = Depends(get_db),
) -> Attendance:
    """指定IDの勤怠を更新する。

    Args:
        attendance_id: 更新対象の勤怠ID。
        attendance_in: 更新内容。
        db: DB session。

    Returns:
        更新後の勤怠record。

    Raises:
        HTTPException: 対象勤怠または指定locationが存在しない場合。
    """
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
    """指定IDの勤怠を削除する。

    Args:
        attendance_id: 削除対象の勤怠ID。
        db: DB session。

    Returns:
        bodyなしの204 response。

    Raises:
        HTTPException: 対象勤怠が存在しない場合。
    """
    attendance_service.delete_attendance(db, attendance_id=attendance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_by_user_date(
    user_id: str,
    date: Date,
    db: Session = Depends(get_db),
) -> Response:
    """user/dateで勤怠を削除する。

    Args:
        user_id: 削除対象user ID。
        date: 削除対象日。
        db: DB session。

    Returns:
        bodyなしの204 response。

    Raises:
        HTTPException: 対象勤怠が存在しない場合。
    """
    attendance_service.delete_attendance_by_user_date(
        db,
        user_id=user_id,
        attendance_date=date,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
