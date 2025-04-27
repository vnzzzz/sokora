"""
勤怠記録CRUD操作
=======================

勤怠記録モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy.orm import Session, load_only
import time

from .base import CRUDBase
from app.models.attendance import Attendance
from app.models.user import User
from app.models.location import Location
from app.models.user_type import UserType
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.core.config import logger


class CRUDAttendance(CRUDBase[Attendance, AttendanceCreate, AttendanceUpdate]):
    """勤怠記録モデルのCRUD操作クラス"""

    # キャッシュの追加（パフォーマンス最適化）
    _day_data_cache: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
    _cache_ttl = 60  # キャッシュの有効期間（秒）
    _cache_timestamp: Dict[str, float] = {}

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
        try:
            attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
            if attendance:
                db.delete(attendance)
                # commitはupdate_user_entryで行うため、ここではしない
                return True
            return False
        except Exception as e:
            logger.error(f"勤怠削除エラー: {str(e)}", exc_info=True)
            return False

    def delete_by_user_and_date(self, db: Session, *, user_id: str, date_obj: date) -> bool:
        """
        指定されたユーザーIDと日付の勤怠記録を削除します。

        Args:
            db: データベースセッション
            user_id: ユーザーID
            date_obj: 日付オブジェクト

        Returns:
            bool: 削除に成功した場合はTrue、対象が見つからない場合はFalse
        """
        obj = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
        if obj:
            logger.debug(f"勤怠レコード削除実行: id={obj.id}, user_id={user_id}, date={date_obj}")
            # super().remove(db=db, id=obj.id) を使うと commit までしてしまう可能性がある
            # CRUDBase の remove は commit を含まないが、念のため直接 delete を呼ぶ
            db.delete(obj)
            # commit は API 層で行う
            # キャッシュをクリアする
            day_key = date_obj.strftime("%Y-%m-%d")
            if day_key in self._day_data_cache:
                del self._day_data_cache[day_key]
                logger.debug(f"日別キャッシュクリア: {day_key}")
            return True
        logger.debug(f"削除対象の勤怠レコードが見つかりません: user_id={user_id}, date={date_obj}")
        return False

    def update_attendance(
        self, db: Session, *, user_id: str, date_obj: date, location_id: int
    ) -> Optional[Attendance]:
        """
        勤怠記録を作成または更新

        Args:
            db: データベースセッション
            user_id: ユーザーID
            date_obj: 日付オブジェクト
            location_id: 勤務場所ID

        Returns:
            Optional[Attendance]: 作成または更新された勤怠記録、エラー時はNone
        """
        try:
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
        except Exception as e:
            logger.error(f"勤怠更新/作成エラー: {str(e)}", exc_info=True)
            return None

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
                    # キャッシュをクリアする
                    day_key = date_obj.strftime("%Y-%m-%d")
                    if day_key in self._day_data_cache:
                        del self._day_data_cache[day_key]
                    return True
                else:
                    logger.debug("削除対象のレコードがありませんでした")
                    return True  # レコードがない場合も正常終了とする
            else:
                # 勤怠レコードを更新
                logger.debug(f"勤怠レコード更新開始: user_id={user.user_id}, date={date_obj}, location_id={location_id}")
                attendance_result = self.update_attendance(
                    db, user_id=str(user.user_id), date_obj=date_obj, location_id=location_id
                )
                if attendance_result is not None:
                    db.commit()
                    logger.debug("勤怠レコード更新成功")
                    # キャッシュをクリアする
                    day_key = date_obj.strftime("%Y-%m-%d")
                    if day_key in self._day_data_cache:
                        del self._day_data_cache[day_key]
                    return True
                else:
                    db.rollback()
                    logger.error("勤怠レコード更新失敗")
                    return False
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
        # キャッシュチェック（パフォーマンス最適化）
        current_time = time.time()
        if day in self._day_data_cache and current_time - self._cache_timestamp.get(day, 0) < self._cache_ttl:
            return self._day_data_cache[day]
            
        try:
            # 日付を変換
            try:
                date_obj = datetime.strptime(day, "%Y-%m-%d").date()
            except ValueError:
                logger.error(f"Invalid date format: {day}")
                return {}

            # N+1問題を回避するため、JOINを使用する最適化クエリ
            query = (
                db.query(
                    Attendance.user_id,
                    User.username,
                    User.user_type_id,
                    Location.name.label('location_name'),
                    UserType.name.label('user_type_name')
                )
                .join(User, Attendance.user_id == User.user_id)
                .join(Location, Attendance.location_id == Location.location_id)
                .outerjoin(UserType, User.user_type_id == UserType.user_type_id)
                .filter(Attendance.date == date_obj)
            )
            
            # 1回のクエリで効率的に結果を取得
            results = query.all()

            # 勤務場所ごとにユーザーをグループ化
            location_groups: Dict[str, List[Dict[str, str]]] = {}
            for row in results:
                location_name = row.location_name
                if location_name not in location_groups:
                    location_groups[location_name] = []

                location_groups[location_name].append(
                    {
                        "user_name": row.username,
                        "user_id": row.user_id,
                        "user_type_id": row.user_type_id,
                        "user_type_name": row.user_type_name or ""
                    }
                )

            # キャッシュに結果を保存
            self._day_data_cache[day] = location_groups
            self._cache_timestamp[day] = current_time
            
            return location_groups
        except Exception as e:
            logger.error(f"Error getting day data: {str(e)}")
            return {}

    def get_attendance_data_for_csv(
        self, 
        db: Session, 
        *, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> Dict[str, str]:
        """
        CSV出力用の勤怠データを取得
        
        Args:
            db: データベースセッション
            start_date: 開始日（指定された場合）
            end_date: 終了日（指定された場合）
            
        Returns:
            Dict[str, str]: ユーザーID+日付をキー、勤務場所名を値とするマッピング
        """
        try:
            query = db.query(
                Attendance.user_id,
                Attendance.date,
                Location.name.label("location_name")
            ).join(
                Location, 
                Attendance.location_id == Location.location_id
            )
            
            # 日付範囲が指定されている場合はフィルタを適用
            if start_date and end_date:
                query = query.filter(
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                )
                
            results = query.all()
            
            # ユーザー×日付ごとの勤務場所をマッピング
            user_locations = {}
            for entry in results:
                date_key = entry.date.strftime("%Y-%m-%d")
                user_key = f"{entry.user_id}_{date_key}"
                user_locations[user_key] = entry.location_name
                
            return user_locations
        except Exception as e:
            logger.error(f"Error getting attendance data for CSV: {str(e)}")
            return {}


attendance = CRUDAttendance(Attendance)
