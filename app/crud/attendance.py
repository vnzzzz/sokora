"""
勤怠記録CRUD操作
=======================

勤怠記録モデルの作成、読取、更新、削除操作を提供します。
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
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
        指定されたユーザーIDと日付に合致する勤怠記録を1件取得します。

        Args:
            db: データベースセッション
            user_id: 検索対象のユーザーID
            date: 検索対象の日付

        Returns:
            Optional[Attendance]: 発見された勤怠記録オブジェクト、存在しない場合はNone
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
        指定されたユーザーIDと日付の勤怠記録を削除します。

        注意: この関数は直接コミットを行いません。呼び出し元でコミットが必要です。
        `update_user_entry` から利用されることを想定しています。

        Args:
            db: データベースセッション
            user_id: 削除対象のユーザーID
            date_obj: 削除対象の日付オブジェクト

        Returns:
            bool: 削除が成功した場合はTrue、対象が見つからない場合やエラー時はFalse
        """
        try:
            attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
            if attendance:
                db.delete(attendance)
                # コミットは呼び出し元の `update_user_entry` で実施されます。
                return True
            return False
        except Exception as e:
            logger.error(f"勤怠削除処理中にエラーが発生しました: {str(e)}", exc_info=True)
            return False

    def delete_by_user_and_date(self, db: Session, *, user_id: str, date_obj: date) -> bool:
        """
        指定されたユーザーIDと日付の勤怠記録を削除します。

        `delete_attendance` と異なり、この関数はキャッシュのクリアも行います。
        APIエンドポイントなどから直接呼び出されることを想定しています。

        Args:
            db: データベースセッション
            user_id: 削除対象のユーザーID
            date_obj: 削除対象の日付オブジェクト

        Returns:
            bool: 削除に成功した場合はTrue、対象が見つからない場合はFalse
        """
        obj = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
        if obj:
            logger.debug(f"勤怠レコード削除実行: id={obj.id}, user_id={user_id}, date={date_obj}")
            # CRUDBase の remove は内部で commit する可能性があるため、
            # ここでは直接 delete を呼び出し、コミットは呼び出し元に委ねます。
            db.delete(obj)
            # 関連する日のキャッシュを無効化します。
            day_key = date_obj.strftime("%Y-%m-%d")
            if day_key in self._day_data_cache:
                del self._day_data_cache[day_key]
                logger.debug(f"日別キャッシュクリア: {day_key}")
            return True
        logger.debug(f"削除対象の勤怠レコードが見つかりません: user_id={user_id}, date={date_obj}")
        return False

    def delete_attendances_by_user_id(self, db: Session, *, user_id: str) -> int:
        """
        指定されたユーザーIDに紐づく全ての勤怠記録を削除します。

        Args:
            db: データベースセッション
            user_id: 削除対象のユーザーID

        Returns:
            int: 削除されたレコード数
        """
        try:
            num_deleted = db.query(Attendance).filter(Attendance.user_id == user_id).delete()
            # CRUDBaseと異なり、ここではコミットを行わない (呼び出し元に委ねる)
            # キャッシュクリアは不要 (ユーザー自体が削除されるため)
            logger.info(f"ユーザーID '{user_id}' に紐づく勤怠レコードを {num_deleted} 件削除しました。")
            return num_deleted
        except Exception as e:
            logger.error(f"ユーザーID '{user_id}' の勤怠レコード一括削除中にエラーが発生しました: {str(e)}", exc_info=True)
            db.rollback() # エラー発生時はロールバック
            raise  # エラーを再送出して呼び出し元に通知

    def update_attendance(
        self, db: Session, *, user_id: str, date_obj: date, location_id: int, note: Optional[str] = None
    ) -> Optional[Attendance]:
        """
        指定されたユーザーIDと日付の勤怠記録を作成または更新します。

        該当する日付の記録が存在すれば更新し、存在しなければ新規作成します。

        Args:
            db: データベースセッション
            user_id: 対象のユーザーID
            date_obj: 対象の日付オブジェクト
            location_id: 設定する勤怠種別ID
            note: 備考

        Returns:
            Optional[Attendance]: 作成または更新された勤怠記録オブジェクト、エラー時はNone
        """
        try:
            # 既存の記録を検索
            attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)

            if attendance:
                # 既存レコードを更新
                return self.update(db, db_obj=attendance, obj_in={"location_id": location_id, "note": note})
            else:
                # 新規レコードを作成
                attendance_in = AttendanceCreate(
                    user_id=user_id,
                    date=date_obj,
                    location_id=location_id,
                    note=note
                )
                return self.create(db, obj_in=attendance_in)
        except Exception as e:
            logger.error(f"勤怠情報の更新または作成中にエラーが発生しました: {str(e)}", exc_info=True)
            return None

    def update_user_entry(
        self, db: Session, *, user_id: str, date_str: str, location_id: int, note: Optional[str] = None
    ) -> bool:
        """
        ユーザーの特定の日付における勤怠情報を更新または削除します。

        location_id に有効なIDが指定された場合は情報を更新し、
        特別な値 (-1) が指定された場合は情報を削除します。
        処理完了後にデータベースのコミットを実行します。

        Args:
            db: データベースセッション
            user_id: 対象のユーザーID文字列
            date_str: 対象の日付文字列 (YYYY-MM-DD形式)
            location_id: 設定する勤怠種別ID。削除の場合は -1 を指定。
            note: 備考

        Returns:
            bool: 処理が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            logger.debug(f"勤怠情報更新/削除処理開始: user_id={user_id}, date={date_str}, location_id={location_id}")

            # 対象ユーザーが存在するか確認
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"指定されたユーザーが見つかりません: user_id={user_id}")
                return False

            # 日付文字列をdateオブジェクトに変換
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                logger.debug(f"日付変換成功: {date_obj}")
            except ValueError:
                logger.error(f"無効な日付形式です: {date_str}")
                return False

            # location_id が -1 の場合は削除処理を実行
            if location_id == -1:
                logger.debug(f"勤怠レコード削除処理開始: user_id={user.id}, date={date_obj}")
                result = self.delete_attendance(db, user_id=str(user.id), date_obj=date_obj)
                if result:
                    db.commit() # 変更を確定
                    logger.debug("勤怠レコード削除成功")
                    # 関連する日のキャッシュを無効化
                    day_key = date_obj.strftime("%Y-%m-%d")
                    if day_key in self._day_data_cache:
                        del self._day_data_cache[day_key]
                    return True
                else:
                    # 削除対象が存在しなかった場合も正常とみなす
                    logger.debug("削除対象のレコードが存在しませんでした。")
                    return True
            else:
                # location_id が有効な場合は更新または新規作成処理を実行
                logger.debug(f"勤怠レコード更新/作成処理開始: user_id={user.id}, date={date_obj}, location_id={location_id}")
                attendance_result = self.update_attendance(
                    db, user_id=str(user.id), date_obj=date_obj, location_id=location_id, note=note
                )
                if attendance_result is not None:
                    db.commit() # 変更を確定
                    logger.debug("勤怠レコード更新/作成成功")
                    # 関連する日のキャッシュを無効化
                    day_key = date_obj.strftime("%Y-%m-%d")
                    if day_key in self._day_data_cache:
                        del self._day_data_cache[day_key]
                    return True
                else:
                    db.rollback() # エラー発生時はロールバック
                    logger.error("勤怠レコード更新/作成失敗")
                    return False
        except Exception as e:
            db.rollback() # 予期せぬエラー発生時もロールバック
            logger.error(f"勤怠情報更新/削除処理中に予期せぬエラーが発生しました: {str(e)}", exc_info=True)
            return False

    def get_user_data(self, db: Session, *, user_id: str) -> List[Dict[str, Any]]:
        """
        指定されたユーザーの全ての勤怠データを取得します。

        Args:
            db: データベースセッション
            user_id: 対象のユーザーID文字列

        Returns:
            List[Dict[str, Any]]: 勤怠データのリスト。各要素は日付、勤怠種別ID、勤怠種別名、備考を含む辞書。
                                 ユーザーが存在しない場合やエラー時は空リストを返します。
        """
        try:
            # 対象ユーザーを取得
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"データ取得対象のユーザーが見つかりません: user_id={user_id}")
                return []

            # ユーザーの勤怠記録と関連する勤怠種別情報を結合して取得
            results = (
                db.query(Attendance, Location)
                .filter(Attendance.user_id == user.id)
                .join(Location, Attendance.location_id == Location.id)
                .all()
            )

            # 取得結果を整形してリスト化
            entries = []
            for attendance, location in results:
                entries.append(
                    {
                        "id": attendance.id, # レコード識別用のID
                        "date": attendance.date.strftime("%Y-%m-%d"),
                        "location_id": attendance.location_id,
                        "location_name": location.name,
                        "note": attendance.note  # 備考フィールドを追加
                    }
                )

            return entries
        except Exception as e:
            logger.error(f"ユーザー勤怠データ取得中にエラーが発生しました: {str(e)}", exc_info=True)
            return []

    def get_day_data(self, db: Session, *, day: str) -> Dict[str, List[Dict[str, str]]]:
        """
        指定した日の全ユーザーの勤怠データを取得

        Args:
            db: データベースセッション
            day: 日付文字列 (YYYY-MM-DD)

        Returns:
            Dict[str, List[Dict[str, str]]]: 勤怠種別ごとにグループ化された勤怠データ
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
                    Attendance.note,  # 備考フィールドを追加
                    User.username,
                    User.user_type_id,
                    Location.name.label('location_name'),
                    UserType.name.label('user_type_name')
                )
                .join(User, Attendance.user_id == User.id)
                .join(Location, Attendance.location_id == Location.id)
                .outerjoin(UserType, User.user_type_id == UserType.id)
                .filter(Attendance.date == date_obj)
            )
            
            # 1回のクエリで効率的に結果を取得
            results = query.all()

            # 勤怠種別ごとにユーザーをグループ化
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
                        "user_type_name": row.user_type_name or "",
                        "note": row.note  # 備考フィールドを追加
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
            Dict[str, str]: ユーザーID+日付をキー、勤怠種別名を値とするマッピング
        """
        try:
            query = db.query(
                Attendance.user_id,
                Attendance.date,
                Location.name.label("location_name")
            ).join(
                Location, 
                Attendance.location_id == Location.id
            )
            
            # 日付範囲が指定されている場合はフィルタを適用
            if start_date and end_date:
                query = query.filter(
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                )
                
            results = query.all()
            
            # ユーザー×日付ごとの勤怠種別をマッピング
            user_locations = {}
            for entry in results:
                date_key = entry.date.strftime("%Y-%m-%d")
                user_key = f"{entry.user_id}_{date_key}"
                user_locations[user_key] = entry.location_name
                
            return user_locations
        except Exception as e:
            logger.error(f"Error getting attendance data for CSV: {str(e)}")
            return {}

    def get_attendance_analysis_data(
        self, db: Session, *, month: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        勤怠分析用のデータを取得します。
        月別・人別・勤怠種別別の日数集計を行います。

        Args:
            db: データベースセッション
            month: 対象月（YYYY-MM形式、指定がない場合は現在の月）

        Returns:
            Dict[str, Any]: 分析データ
                - month_name: 月名（例: "2024年1月"）
                - users: ユーザー別の勤怠データ
                - locations: 勤怠種別一覧
                - summary: 集計サマリー
        """
        from datetime import datetime, date
        import calendar
        from app.crud.user import user as user_crud
        from app.crud.location import location as location_crud
        from app.crud.group import group as group_crud
        from app.crud.user_type import user_type as user_type_crud
        from sqlalchemy import func, and_

        try:
            # 対象月の決定
            if month is None:
                current_date = datetime.now()
                month = f"{current_date.year}-{current_date.month:02d}"
            
            # 月の解析
            year, month_num = map(int, month.split('-'))
            month_name = f"{year}年{month_num}月"
            
            # 月の開始日と終了日を計算
            first_day = date(year, month_num, 1)
            last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])
            
            # ユーザー情報を取得（グループ、ユーザー種別含む）
            users_data = user_crud.get_all_users_with_details(db)
            
            # 勤怠種別情報を取得
            locations = location_crud.get_multi(db)
            locations_sorted = sorted(locations, key=lambda x: (x.order or 999, x.id))
            
            # 対象期間の勤怠データを取得
            attendances = (
                db.query(Attendance)
                .filter(
                    and_(
                        Attendance.date >= first_day,
                        Attendance.date <= last_day
                    )
                )
                .all()
            )
            
            # ユーザー別・勤怠種別別の日数を集計
            user_analysis = {}
            location_totals = {loc.id: 0 for loc in locations_sorted}
            
            for user_data in users_data:
                user_name, user_id, group_name, user_type_name = user_data
                
                # このユーザーの勤怠データを集計
                user_attendances = [att for att in attendances if att.user_id == user_id]
                location_counts = {loc.id: 0 for loc in locations_sorted}
                
                for att in user_attendances:
                    location_counts[att.location_id] += 1
                    location_totals[att.location_id] += 1
                
                # 総勤務日数を計算
                total_days = sum(location_counts.values())
                
                user_analysis[user_id] = {
                    "user_name": user_name,
                    "group_name": group_name,
                    "user_type_name": user_type_name,
                    "location_counts": location_counts,
                    "total_days": total_days
                }
            
            # 勤怠種別情報を整理
            locations_info = []
            for loc in locations_sorted:
                locations_info.append({
                    "id": loc.id,
                    "name": loc.name,
                    "category": loc.category,
                    "total_days": location_totals[loc.id]
                })
            
            # サマリー情報を計算
            total_users = len(user_analysis)
            total_attendance_days = sum(location_totals.values())
            
            return {
                "month": month,
                "month_name": month_name,
                "users": user_analysis,
                "locations": locations_info,
                "summary": {
                    "total_users": total_users,
                    "total_attendance_days": total_attendance_days,
                    "location_totals": location_totals
                }
            }
            
        except Exception as e:
            logger.error(f"勤怠分析データ取得中にエラーが発生しました: {str(e)}", exc_info=True)
            return {
                "month": month or "",
                "month_name": "エラー",
                "users": {},
                "locations": [],
                "summary": {
                    "total_users": 0,
                    "total_attendance_days": 0,
                    "location_totals": {}
                }
            }


attendance = CRUDAttendance(Attendance)
