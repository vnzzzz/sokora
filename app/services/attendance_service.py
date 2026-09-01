"""勤怠write use caseとtransaction境界を提供するservice。"""

from datetime import date

from sqlalchemy.orm import Session

from app import crud, models
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.errors import ApplicationError, NotFoundError
from app.services.transaction import transaction


def _require_user(db: Session, user_id: str) -> None:
    if crud.user.get(db, id=user_id) is None:
        raise NotFoundError(f"User with id {user_id} not found")


def _require_location(db: Session, location_id: int) -> None:
    if crud.location.get(db, id=location_id) is None:
        raise NotFoundError(f"Location with id {location_id} not found")


def create_attendance(
    db: Session,
    *,
    attendance_in: AttendanceCreate,
) -> models.Attendance:
    """ユーザー・日付・勤怠種別を検証して勤怠を1 transactionで作成します。"""
    duplicate_detail = (
        f"ユーザー '{attendance_in.user_id}' の日付 '{attendance_in.date.isoformat()}' には"
        "既に勤怠データが存在します。"
    )
    with transaction(db, integrity_detail=duplicate_detail):
        _require_user(db, attendance_in.user_id)
        _require_location(db, attendance_in.location_id)

        # 利用者へ既存contractの400を返すため事前チェックする。
        # concurrent writeはDB UNIQUE制約とtransaction helperが最終保証する。
        existing = crud.attendance.get_by_user_and_date(
            db,
            user_id=attendance_in.user_id,
            date=attendance_in.date,
        )
        if existing is not None:
            raise ApplicationError(duplicate_detail)
        created = crud.attendance.create(db, obj_in=attendance_in)
    return created


def update_attendance(
    db: Session,
    *,
    attendance_id: int,
    attendance_in: AttendanceUpdate,
) -> models.Attendance:
    """勤怠IDで既存行を取得し、更新内容を1 transactionで反映します。"""
    with transaction(db, integrity_detail="勤怠データの参照整合性に違反しました"):
        db_obj = crud.attendance.get(db, id=attendance_id)
        if db_obj is None:
            raise NotFoundError(f"Attendance with id {attendance_id} not found")
        if attendance_in.location_id is not None:
            _require_location(db, attendance_in.location_id)
        updated = crud.attendance.update(db, db_obj=db_obj, obj_in=attendance_in)
    return updated


def delete_attendance(db: Session, *, attendance_id: int) -> models.Attendance:
    """勤怠IDで1件削除し、削除したモデルを返します。"""
    with transaction(db):
        db_obj = crud.attendance.get(db, id=attendance_id)
        if db_obj is None:
            raise NotFoundError(f"Attendance with id {attendance_id} not found")
        deleted = crud.attendance.remove(db, id=attendance_id)
    return deleted


def delete_attendance_by_user_date(
    db: Session, *, user_id: str, attendance_date: date
) -> models.Attendance:
    """ユーザーと日付で勤怠を1件削除します。"""
    with transaction(db):
        db_obj = crud.attendance.get_by_user_and_date(
            db, user_id=user_id, date=attendance_date
        )
        if db_obj is None:
            raise NotFoundError(
                f"ユーザー '{user_id}' の日付 '{attendance_date.isoformat()}' "
                "の勤怠データが見つかりません"
            )
        deleted = crud.attendance.remove(db, id=int(db_obj.id))
    return deleted
