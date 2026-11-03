"""勤怠write use caseとtransaction境界を提供するservice。"""

from datetime import date

from sqlalchemy.orm import Session

from app import crud, models
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.errors import ApplicationError, NotFoundError
from app.services.transaction import transaction


def _require_user(db: Session, user_id: str) -> None:
    """対象userの存在を検証する。

    Args:
        db: DB session。
        user_id: 検証対象user ID。

    Raises:
        NotFoundError: userが存在しない場合。
    """
    if crud.user.get(db, id=user_id) is None:
        raise NotFoundError(f"User with id {user_id} not found")


def _require_location(db: Session, location_id: int) -> None:
    """対象勤怠種別の存在を検証する。

    Args:
        db: DB session。
        location_id: 検証対象の勤怠種別ID。

    Raises:
        NotFoundError: 勤怠種別が存在しない場合。
    """
    if crud.location.get(db, id=location_id) is None:
        raise NotFoundError(f"Location with id {location_id} not found")


def create_attendance(
    db: Session,
    *,
    attendance_in: AttendanceCreate,
) -> models.Attendance:
    """ユーザー・日付・勤怠種別を検証して勤怠を1 transactionで作成する。

    Args:
        db: DB session。
        attendance_in: 作成する勤怠データ。

    Returns:
        作成後の勤怠model。

    Raises:
        NotFoundError: userまたは勤怠種別が存在しない場合。
        ApplicationError: 同一user/dateの勤怠が既に存在する場合。
    """
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
    """勤怠IDで既存行を取得し、更新内容を1 transactionで反映する。

    Args:
        db: DB session。
        attendance_id: 更新対象の勤怠ID。
        attendance_in: 更新内容。

    Returns:
        更新後の勤怠model。

    Raises:
        NotFoundError: 勤怠または指定勤怠種別が存在しない場合。
    """
    with transaction(db, integrity_detail="勤怠データの参照整合性に違反しました"):
        db_obj = crud.attendance.get(db, id=attendance_id)
        if db_obj is None:
            raise NotFoundError(f"Attendance with id {attendance_id} not found")
        if attendance_in.location_id is not None:
            _require_location(db, attendance_in.location_id)
        updated = crud.attendance.update(db, db_obj=db_obj, obj_in=attendance_in)
    return updated


def delete_attendance(db: Session, *, attendance_id: int) -> models.Attendance:
    """勤怠IDで1件削除する。

    Args:
        db: DB session。
        attendance_id: 削除対象の勤怠ID。

    Returns:
        削除した勤怠model。

    Raises:
        NotFoundError: 対象勤怠が存在しない場合。
    """
    with transaction(db):
        db_obj = crud.attendance.get(db, id=attendance_id)
        if db_obj is None:
            raise NotFoundError(f"Attendance with id {attendance_id} not found")
        deleted = crud.attendance.remove(db, id=attendance_id)
    return deleted


def delete_attendance_by_user_date(
    db: Session, *, user_id: str, attendance_date: date
) -> models.Attendance:
    """user/dateで勤怠を1件削除する。

    Args:
        db: DB session。
        user_id: 削除対象user ID。
        attendance_date: 削除対象日。

    Returns:
        削除した勤怠model。

    Raises:
        NotFoundError: 対象勤怠が存在しない場合。
    """
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
