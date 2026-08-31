"""勤怠記録のpersistence queryを提供する。"""

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import logger
from app.models.attendance import Attendance
from app.models.location import Location
from app.models.user import User
from app.models.user_type import UserType
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate

from .base import CRUDBase


class CRUDAttendance(CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate]):
    """Attendance rowのCRUDとread queryだけを担当する。"""

    def get_by_user_and_date(
        self, db: Session, *, user_id: str, date: date
    ) -> Optional[Attendance]:
        return (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id, Attendance.date == date)
            .first()
        )

    def delete_attendances_by_user_id(self, db: Session, *, user_id: str) -> int:
        """指定ユーザーの勤怠を一括削除対象としてflushする。"""
        num_deleted = (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "ユーザーID '%s' に紐づく勤怠レコードを %s 件削除しました。",
            user_id,
            num_deleted,
        )
        return num_deleted

    def get_user_data(self, db: Session, *, user_id: str) -> List[Dict[str, Any]]:
        """指定ユーザーの勤怠と勤怠種別を1 queryで取得し表示用rowへ投影する。"""
        rows = (
            db.query(Attendance, Location)
            .filter(Attendance.user_id == user_id)
            .join(Location, Attendance.location_id == Location.id)
            .all()
        )
        return [
            {
                "id": attendance.id,
                "date": attendance.date.strftime("%Y-%m-%d"),
                "location_id": attendance.location_id,
                "location_name": location.name,
                "note": attendance.note,
            }
            for attendance, location in rows
        ]

    def get_day_data(self, db: Session, *, day: str) -> Dict[str, List[Dict[str, str]]]:
        """指定日の勤怠を勤怠種別ごとに返す。process-local cacheは持たない。"""
        try:
            date_obj = date.fromisoformat(day)
        except ValueError:
            return {}

        rows = (
            db.query(
                Attendance.user_id,
                Attendance.note,
                User.username,
                User.user_type_id,
                Location.name.label("location_name"),
                UserType.name.label("user_type_name"),
            )
            .join(User, Attendance.user_id == User.id)
            .join(Location, Attendance.location_id == Location.id)
            .outerjoin(UserType, User.user_type_id == UserType.id)
            .filter(Attendance.date == date_obj)
            .all()
        )

        location_groups: Dict[str, List[Dict[str, str]]] = {}
        for row in rows:
            location_name = str(row.location_name)
            location_groups.setdefault(location_name, []).append(
                {
                    "user_name": str(row.username),
                    "user_id": str(row.user_id),
                    "user_type_id": str(row.user_type_id),
                    "user_type_name": str(row.user_type_name or ""),
                    "note": str(row.note or ""),
                }
            )
        return location_groups

    def list_for_period(
        self, db: Session, *, start_date: date, end_date: date
    ) -> List[Attendance]:
        """期間内の勤怠modelを日付順で取得する。"""
        return (
            db.query(Attendance)
            .filter(Attendance.date >= start_date, Attendance.date <= end_date)
            .order_by(Attendance.date)
            .all()
        )

    def list_export_rows(
        self,
        db: Session,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Any]:
        """CSV出力に必要なuser/date/location nameだけを取得する。"""
        query = db.query(
            Attendance.user_id,
            Attendance.date,
            Location.name.label("location_name"),
        ).join(Location, Attendance.location_id == Location.id)
        if start_date is not None and end_date is not None:
            query = query.filter(
                Attendance.date >= start_date,
                Attendance.date <= end_date,
            )
        return list(query.all())


attendance = CRUDAttendance(Attendance)
