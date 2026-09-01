"""カレンダー表示用のpersistence queryを提供する。"""

from datetime import date, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import Attendance
from app.models.group import Group
from app.models.location import Location
from app.models.user import User
from app.models.user_type import UserType


class CRUDCalendar:
    """Calendar read modelが必要とするqueryだけを担当する。"""

    def get_month_attendances(
        self, db: Session, *, first_day: date, last_day: date
    ) -> List[Attendance]:
        """指定期間の勤怠をlocation込みで一括取得する。"""
        return (
            db.query(Attendance)
            .options(joinedload(Attendance.location_info))
            .filter(Attendance.date >= first_day, Attendance.date <= last_day)
            .all()
        )

    def get_week_attendances(self, db: Session, *, monday: date) -> List[Attendance]:
        """週内の勤怠をlocation込みで一括取得する。"""
        sunday = monday + timedelta(days=6)
        return (
            db.query(Attendance)
            .options(joinedload(Attendance.location_info))
            .filter(Attendance.date >= monday, Attendance.date <= sunday)
            .all()
        )

    def get_week_attendance_counts(
        self, db: Session, *, monday: date
    ) -> Dict[int, int]:
        """週内の日付ごとの勤怠件数を返す。"""
        sunday = monday + timedelta(days=6)
        rows = (
            db.query(
                func.extract("day", Attendance.date).label("day"),
                func.count("*").label("count"),
            )
            .filter(and_(Attendance.date >= monday, Attendance.date <= sunday))
            .group_by(func.extract("day", Attendance.date))
            .all()
        )
        return {int(day): int(count) for day, count in rows}

    def count_day_attendances(self, db: Session, *, target_date: date) -> int:
        """指定日の勤怠件数を返す。"""
        return db.query(Attendance).filter(Attendance.date == target_date).count()

    def get_month_attendance_counts(
        self, db: Session, *, first_day: date, last_day: date
    ) -> Dict[int, int]:
        """月内の日付ごとの勤怠件数を返す。"""
        rows = (
            db.query(
                func.extract("day", Attendance.date).label("day"),
                func.count("*").label("count"),
            )
            .filter(and_(Attendance.date >= first_day, Attendance.date <= last_day))
            .group_by(func.extract("day", Attendance.date))
            .all()
        )
        return {int(day): int(count) for day, count in rows}

    def list_locations(self, db: Session) -> List[Location]:
        """全勤怠種別をID順で取得する。"""
        return list(db.query(Location).order_by(Location.id).all())

    def get_day_attendance_rows(self, db: Session, *, target_date: date) -> List[Any]:
        """日別表示に必要な関連情報を1 queryで取得する。"""
        return list(
            db.query(
                Attendance.user_id,
                Attendance.note,
                User.username.label("user_name"),
                User.group_id,
                Group.name.label("group_name"),
                Group.order.label("group_order"),
                User.user_type_id,
                UserType.name.label("user_type_name"),
                UserType.order.label("user_type_order"),
                Attendance.location_id,
                Location.name.label("location_name"),
            )
            .select_from(Attendance)
            .join(User, Attendance.user_id == User.id)
            .join(Group, User.group_id == Group.id)
            .join(UserType, User.user_type_id == UserType.id)
            .join(Location, Attendance.location_id == Location.id)
            .filter(Attendance.date == target_date)
            .all()
        )


calendar = CRUDCalendar()
calendar_crud = calendar
