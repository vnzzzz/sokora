"""勤怠記録のpersistence queryを提供する。"""

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.config import logger
from app.models.attendance import Attendance
from app.models.location import Location
from app.models.user import User
from app.models.user_type import UserType
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate

from .base import CRUDBase


class CRUDAttendance(CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate]):
    """Attendance rowのCRUDとread queryだけを担当する。"""

    def list_all(self, db: Session) -> List[Attendance]:
        """全勤怠recordをpaginationなしで取得する。

        Args:
            db: DB session。

        Returns:
            全勤怠recordのlist。
        """
        return list(db.query(Attendance).all())

    def get_by_user_and_date(
        self, db: Session, *, user_id: str, date: date
    ) -> Optional[Attendance]:
        """user/dateで勤怠を1件取得する。

        Args:
            db: DB session。
            user_id: 対象user ID。
            date: 対象日。

        Returns:
            一致する勤怠record。存在しない場合は`None`。
        """
        return (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id, Attendance.date == date)
            .first()
        )

    def delete_attendances_by_user_id(self, db: Session, *, user_id: str) -> int:
        """指定userの勤怠を一括削除対象としてflushする。

        Args:
            db: DB session。
            user_id: 対象user ID。

        Returns:
            削除stageした勤怠record数。

        Notes:
            commit/rollbackは呼び出し側が所有する。
        """
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
        """指定userの勤怠と勤怠種別を表示用rowへ投影する。

        Args:
            db: DB session。
            user_id: 対象user ID。

        Returns:
            勤怠ID、日付、勤怠種別、noteを含むdisplay rowのlist。
        """
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

    def list_user_for_period(
        self,
        db: Session,
        *,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Attendance]:
        """1 userの期間内勤怠をlocation込みで日付順に取得する。

        Args:
            db: DB session。
            user_id: 対象user ID。
            start_date: inclusiveな期間開始日。
            end_date: inclusiveな期間終了日。

        Returns:
            location relationをeager-loadした勤怠modelのlist。
        """
        return list(
            db.query(Attendance)
            .options(joinedload(Attendance.location_info))
            .filter(
                Attendance.user_id == user_id,
                Attendance.date >= start_date,
                Attendance.date <= end_date,
            )
            .order_by(Attendance.date)
            .all()
        )

    def get_day_data(
        self, db: Session, *, day: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """指定日の勤怠を勤怠種別ごとに投影する。

        input validationはadapterが所有する。

        Args:
            db: DB session。
            day: 対象日。

        Returns:
            勤怠種別名をkey、user detail listをvalueとするmapping。
        """
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
            .filter(Attendance.date == day)
            .all()
        )

        location_groups: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            location_name = str(row.location_name)
            location_groups.setdefault(location_name, []).append(
                {
                    "user_name": row.username,
                    "user_id": row.user_id,
                    "user_type_id": row.user_type_id,
                    "user_type_name": row.user_type_name or "",
                    "note": row.note,
                }
            )
        return location_groups

    def list_for_period(
        self, db: Session, *, start_date: date, end_date: date
    ) -> List[Attendance]:
        """期間内の勤怠modelを日付順で取得する。

        Args:
            db: DB session。
            start_date: inclusiveな期間開始日。
            end_date: inclusiveな期間終了日。

        Returns:
            日付順の勤怠model list。
        """
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
        """CSV出力に必要なuser/date/locationだけを取得する。

        Args:
            db: DB session。
            start_date: optionalなinclusive開始日。
            end_date: optionalなinclusive終了日。

        Returns:
            user ID、日付、勤怠種別名を持つquery rowのlist。

        Notes:
            期間filterはstart/endの両方が指定された場合だけ適用する。
        """
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
