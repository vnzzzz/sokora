"""
Attendance CRUD operations
=======================

Create, Read, Update, Delete operations for Attendance model.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.attendance import Attendance
from ..models.user import User
from ..schemas.attendance import AttendanceCreate, AttendanceUpdate


class CRUDAttendance(CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate]):
    """出席記録モデルのCRUD操作クラス"""

    def get_by_user_and_date(
        self, db: Session, *, user_id: int, date: date
    ) -> Optional[Attendance]:
        """
        ユーザーIDと日付で出席記録を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID（データベースID）
            date: 日付

        Returns:
            Optional[Attendance]: 見つかった出席記録、またはNone
        """
        return (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id, Attendance.date == date)
            .first()
        )

    def update_attendance(
        self, db: Session, *, user_id: int, date_obj: date, location: str
    ) -> Attendance:
        """
        出席記録を作成または更新

        Args:
            db: データベースセッション
            user_id: ユーザーID（データベースID）
            date_obj: 日付
            location: 勤務場所

        Returns:
            Attendance: 作成または更新された出席記録
        """
        # 既存の記録を確認
        attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)

        if attendance:
            # 既存の記録を更新
            return self.update(db, db_obj=attendance, obj_in={"location": location})
        else:
            # 新しい記録を作成
            attendance_in = AttendanceCreate(
                user_id=user_id, date=date_obj, location=location
            )
            return self.create(db, obj_in=attendance_in)

    def update_user_entry(
        self, db: Session, *, user_id: str, date_str: str, location: str
    ) -> bool:
        """
        ユーザーの出席情報を更新

        Args:
            db: データベースセッション
            user_id: ユーザーID文字列
            date_str: 日付文字列 (YYYY-MM-DD)
            location: 勤務場所

        Returns:
            bool: 成功したかどうか
        """
        try:
            # ユーザーを取得
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return False

            # 日付を変換
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return False

            # 出席レコードを更新
            self.update_attendance(
                db, user_id=user.id, date_obj=date_obj, location=location
            )
            return True
        except Exception:
            db.rollback()
            return False

    def get_user_data(self, db: Session, *, user_id: str) -> List[Dict[str, str]]:
        """
        ユーザーの全出席データを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID文字列

        Returns:
            List[Dict[str, str]]: 出席データリスト
        """
        try:
            # ユーザーを取得
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return []

            # ユーザーの出席レコードを取得
            attendances = (
                db.query(Attendance).filter(Attendance.user_id == user.id).all()
            )

            # データを整形
            entries = []
            for attendance in attendances:
                entries.append(
                    {
                        "date": attendance.date.strftime("%Y-%m-%d"),
                        "location": attendance.location,
                    }
                )

            return entries
        except Exception:
            return []

    def get_day_data(self, db: Session, *, day: str) -> Dict[str, List[Dict[str, str]]]:
        """
        指定した日の全ユーザーの出席データを取得

        Args:
            db: データベースセッション
            day: 日付文字列 (YYYY-MM-DD)

        Returns:
            Dict[str, List[Dict[str, str]]]: 出席データ
        """
        try:
            # 日付を変換
            try:
                date_obj = datetime.strptime(day, "%Y-%m-%d").date()
            except ValueError:
                return {"users": []}

            # 指定した日の出席レコードを取得
            results = (
                db.query(Attendance, User)
                .join(User, Attendance.user_id == User.id)
                .filter(Attendance.date == date_obj)
                .all()
            )

            # ユーザーごとにデータを整形
            users = []
            for attendance, user in results:
                users.append(
                    {
                        "name": user.username,
                        "user_id": user.user_id,
                        "location": attendance.location,
                    }
                )

            return {"users": users}
        except Exception:
            return {"users": []}


attendance = CRUDAttendance(Attendance)
