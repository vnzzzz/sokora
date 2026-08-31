"""勤怠write use caseとtransaction境界を提供するservice。"""

from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.transaction import transaction


def create_attendance(
    db: Session,
    *,
    user_id: str,
    attendance_date: date,
    location_id: int,
    note: Optional[str] = None,
) -> models.Attendance:
    """ユーザー・日付・勤怠種別を検証して勤怠を1 transactionで作成します。"""
    duplicate_detail = (
        f"ユーザー '{user_id}' の日付 '{attendance_date.isoformat()}' には"
        "既に勤怠データが存在します。"
    )
    with transaction(db, integrity_detail=duplicate_detail):
        crud.user.get_or_404(db, id=user_id)
        crud.location.get_or_404(db, id=location_id)

        # 事前チェックは利用者へ具体的な400を返すために行う。
        # 並行writeで競合した場合はDBのUNIQUE制約が最終的な一意性を保証する。
        existing = crud.attendance.get_by_user_and_date(
            db, user_id=user_id, date=attendance_date
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=duplicate_detail,
            )
        created = crud.attendance.create(
            db,
            obj_in=AttendanceCreate(
                user_id=user_id,
                date=attendance_date,
                location_id=location_id,
                note=note,
            ),
        )
    return created


def update_attendance(
    db: Session,
    *,
    attendance_id: int,
    location_id: int,
    note: Optional[str] = None,
) -> models.Attendance:
    """勤怠IDで既存行を取得し、勤怠種別と備考を1 transactionで更新します。"""
    with transaction(db, integrity_detail="勤怠データの参照整合性に違反しました"):
        db_obj = crud.attendance.get_or_404(db, id=attendance_id)
        crud.location.get_or_404(db, id=location_id)
        updated = crud.attendance.update(
            db,
            db_obj=db_obj,
            obj_in=AttendanceUpdate(location_id=location_id, note=note),
        )
    return updated


def delete_attendance(db: Session, *, attendance_id: int) -> models.Attendance:
    """勤怠IDで1件削除し、削除したモデルを返します。"""
    with transaction(db):
        db_obj = crud.attendance.get_or_404(db, id=attendance_id)
        deleted = crud.attendance.remove(db, id=db_obj.id)
    return deleted


def delete_attendance_by_user_date(
    db: Session, *, user_id: str, attendance_date: date
) -> models.Attendance:
    """ユーザーと日付で勤怠を1件削除し、存在しない場合はHTTP 404を送出します。"""
    with transaction(db):
        db_obj = crud.attendance.get_by_user_and_date(
            db, user_id=user_id, date=attendance_date
        )
        if db_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"ユーザー '{user_id}' の日付 '{attendance_date.isoformat()}' "
                    "の勤怠データが見つかりません"
                ),
            )
        deleted = crud.attendance.remove(db, id=db_obj.id)
    return deleted
