"""
勤怠記録CRUD操作
=======================

勤怠記録モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.attendance import Attendance
from ..models.user import User
from ..models.location import Location
from ..schemas.attendance import AttendanceCreate, AttendanceUpdate
from ..core.config import logger


class CRUDAttendance(CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate]):
    """勤怠記録モデルのCRUD操作クラス"""

    def get_by_user_and_date(
        self, db: Session, *, user_id: str, date: date
    ) -> Optional[Attendance]:
        """
        ユーザーIDと日付で勤怠記録を取得

        Args:
            db: データベースセッション
            user_id: ユーザーID
            date: 日付

        Returns:
            Optional[Attendance]: 見つかった勤怠記録、またはNone
        """
        return (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id, Attendance.date == date)
            .first()
        )

    def delete_attendance(
        self, db: Session, *, user_id: str, date_obj: date
    ) -> bool:
        """
        勤怠記録を削除

        Args:
            db: データベースセッション
            user_id: ユーザーID
            date_obj: 日付オブジェクト

        Returns:
            bool: 削除に成功したかどうか
        """
        attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
        if attendance:
            db.delete(attendance)
            return True
        return False

    def update_attendance(
        self, db: Session, *, user_id: str, date_obj: date, location_id: int
    ) -> Attendance:
        """
        勤怠記録を作成または更新

        Args:
            db: データベースセッション
            user_id: ユーザーID
            date_obj: 日付オブジェクト
            location_id: 勤務場所ID

        Returns:
            Attendance: 作成または更新された勤怠記録
        """
        # 既存の記録を確認
        attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)

        if attendance:
            # 既存の記録を更新
            return self.update(db, db_obj=attendance, obj_in={"location_id": location_id})
        else:
            # 新しい記録を作成
            attendance_in = AttendanceCreate(
                user_id=user_id,
                date=date_obj,  # dateオブジェクトを直接渡す
                location_id=location_id
            )
            return self.create(db, obj_in=attendance_in)

    def update_user_entry(
        self, db: Session, *, user_id: str, date_str: str, location_id: int
    ) -> bool:
        """
        ユーザーの勤怠情報を更新

        Args:
            db: データベースセッション
            user_id: ユーザーID文字列
            date_str: 日付文字列 (YYYY-MM-DD)
            location_id: 勤務場所ID

        Returns:
            bool: 成功したかどうか
        """
        try:
            logger.debug(f"勤怠更新開始: user_id={user_id}, date={date_str}, location_id={location_id}")
            
            # ユーザーを取得
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                logger.error(f"ユーザーが見つかりません: user_id={user_id}")
                return False

            # 日付を変換
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                logger.debug(f"日付変換成功: {date_obj}")
            except ValueError:
                logger.error(f"日付形式が無効です: {date_str}")
                return False

            # 削除オプションの場合（従来の特別なケース用）
            if location_id == -1:  # 削除用の特別な値
                logger.debug(f"勤怠レコード削除開始: user_id={user.user_id}, date={date_obj}")
                result = self.delete_attendance(db, user_id=str(user.user_id), date_obj=date_obj)
                if result:
                    db.commit()
                    logger.debug("勤怠レコード削除成功")
                    return True
                else:
                    logger.debug("削除対象のレコードがありませんでした")
                    return True  # レコードがない場合も正常終了とする
            else:
                # 勤怠レコードを更新
                logger.debug(f"勤怠レコード更新開始: user_id={user.user_id}, date={date_obj}, location_id={location_id}")
                self.update_attendance(
                    db, user_id=str(user.user_id), date_obj=date_obj, location_id=location_id
                )
                db.commit()
                logger.debug("勤怠レコード更新成功")
                return True
        except Exception as e:
            db.rollback()
            logger.error(f"勤怠更新エラー: {str(e)}", exc_info=True)
            return False

    def get_user_data(self, db: Session, *, user_id: str) -> List[Dict[str, Any]]:
        """
        ユーザーの全勤怠データを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID文字列

        Returns:
            List[Dict[str, Any]]: 勤怠データリスト
        """
        try:
            # ユーザーを取得
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return []

            # ユーザーの勤怠レコードを取得（勤務場所の情報も含める）
            results = (
                db.query(Attendance, Location)
                .filter(Attendance.user_id == user.user_id)
                .join(Location, Attendance.location_id == Location.location_id)
                .all()
            )

            # データを整形
            entries = []
            for attendance, location in results:
                entries.append(
                    {
                        "id": attendance.id,  # 勤怠IDを追加
                        "date": attendance.date.strftime("%Y-%m-%d"),
                        "location_id": attendance.location_id,
                        "location_name": location.name
                    }
                )

            return entries
        except Exception as e:
            logger.error(f"Error getting user data: {str(e)}")
            return []

    def get_day_data(self, db: Session, *, day: str) -> Dict[str, List[Dict[str, str]]]:
        """
        指定した日の全ユーザーの勤怠データを取得

        Args:
            db: データベースセッション
            day: 日付文字列 (YYYY-MM-DD)

        Returns:
            Dict[str, List[Dict[str, str]]]: 勤務場所ごとにグループ化された勤怠データ
        """
        try:
            # 日付を変換
            try:
                date_obj = datetime.strptime(day, "%Y-%m-%d").date()
            except ValueError:
                logger.error(f"Invalid date format: {day}")
                return {}

            # 指定した日の勤怠レコードを取得
            results = (
                db.query(Attendance, User, Location)
                .join(User, Attendance.user_id == User.user_id)
                .join(Location, Attendance.location_id == Location.location_id)
                .filter(Attendance.date == date_obj)
                .all()
            )

            # 勤務場所ごとにユーザーをグループ化
            location_groups: Dict[str, List[Dict[str, str]]] = {}
            for attendance, user, location in results:
                location_name = location.name
                if location_name not in location_groups:
                    location_groups[location_name] = []

                location_groups[location_name].append(
                    {
                        "user_name": user.username,
                        "user_id": user.user_id,
                        "is_contractor": user.is_contractor,
                    }
                )

            return location_groups
        except Exception as e:
            logger.error(f"Error getting day data: {str(e)}")
            return {}


attendance = CRUDAttendance(Attendance)
