"""
勤怠記録CRUD操作
=======================

勤怠記録モデルの作成、読取、更新、削除操作を提供します。
"""

import time
from datetime import date, datetime
from types import SimpleNamespace
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
    """勤怠記録モデルのCRUD操作クラス"""

    # 日別表示のread cacheはprocess-localで共有する。write pathでは対象日を
    # invalidateし、rollback時に余分なinvalidateが起きても次回readで再構築する。
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

    def delete_attendance(self, db: Session, *, user_id: str, date_obj: date) -> bool:
        """ユーザーと日付に一致する勤怠を削除対象としてflushします。

        対象が無い場合はFalseを返します。commit/rollbackは呼び出し側serviceが所有します。
        """
        attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
        if attendance is None:
            return False
        db.delete(attendance)
        db.flush()
        return True

    def delete_by_user_and_date(
        self, db: Session, *, user_id: str, date_obj: date
    ) -> bool:
        """ユーザーと日付に一致する勤怠を削除対象としてflushし、該当日のread cacheを無効化します。

        対象が無い場合はFalseを返し、transactionの確定は呼び出し側へ委ねます。
        """
        obj = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
        if obj is None:
            logger.debug(
                f"削除対象の勤怠レコードが見つかりません: user_id={user_id}, date={date_obj}"
            )
            return False

        logger.debug(
            f"勤怠レコード削除実行: id={obj.id}, user_id={user_id}, date={date_obj}"
        )
        db.delete(obj)
        db.flush()
        self._day_data_cache.pop(date_obj.strftime("%Y-%m-%d"), None)
        return True

    def delete_attendances_by_user_id(self, db: Session, *, user_id: str) -> int:
        """指定ユーザーの勤怠を一括で削除対象としてflushし、対象件数を返します。

        user削除など複数tableを扱うservice transaction内で使用します。
        """
        num_deleted = (
            db.query(Attendance)
            .filter(Attendance.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            f"ユーザーID '{user_id}' に紐づく勤怠レコードを {num_deleted} 件削除しました。"
        )
        return num_deleted

    def update_attendance(
        self,
        db: Session,
        *,
        user_id: str,
        date_obj: date,
        location_id: int,
        note: Optional[str] = None,
    ) -> Attendance:
        """ユーザーと日付の勤怠を更新し、無ければ新規行をflushします。

        commit/rollbackは呼び出し側serviceが所有します。
        """
        attendance = self.get_by_user_and_date(db, user_id=user_id, date=date_obj)
        if attendance is not None:
            return self.update(
                db,
                db_obj=attendance,
                obj_in={"location_id": location_id, "note": note},
            )

        attendance_in = AttendanceCreate(
            user_id=user_id,
            date=date_obj,
            location_id=location_id,
            note=note,
        )
        return self.create(db, obj_in=attendance_in)

    def update_user_entry(
        self,
        db: Session,
        *,
        user_id: str,
        date_str: str,
        location_id: int,
        note: Optional[str] = None,
    ) -> bool:
        """従来caller向けに日付文字列から勤怠の更新・削除をstageする互換helperです。

        date_strはYYYY-MM-DD、location_id=-1は削除を表します。transactionは確定しません。
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.error(f"指定されたユーザーが見つかりません: user_id={user_id}")
            return False

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"無効な日付形式です: {date_str}")
            return False

        if location_id == -1:
            deleted = self.delete_attendance(
                db,
                user_id=str(user.id),
                date_obj=date_obj,
            )
            if deleted:
                self._day_data_cache.pop(date_obj.strftime("%Y-%m-%d"), None)
            return True

        self.update_attendance(
            db,
            user_id=str(user.id),
            date_obj=date_obj,
            location_id=location_id,
            note=note,
        )
        self._day_data_cache.pop(date_obj.strftime("%Y-%m-%d"), None)
        return True

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
                logger.warning(
                    f"データ取得対象のユーザーが見つかりません: user_id={user_id}"
                )
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
                        "id": attendance.id,  # レコード識別用のID
                        "date": attendance.date.strftime("%Y-%m-%d"),
                        "location_id": attendance.location_id,
                        "location_name": location.name,
                        "note": attendance.note,  # 備考フィールドを追加
                    }
                )

            return entries
        except Exception as e:
            logger.error(
                f"ユーザー勤怠データ取得中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )
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
        if (
            day in self._day_data_cache
            and current_time - self._cache_timestamp.get(day, 0) < self._cache_ttl
        ):
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
                    Location.name.label("location_name"),
                    UserType.name.label("user_type_name"),
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
                        "note": row.note,  # 備考フィールドを追加
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
        end_date: Optional[date] = None,
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
                Location.name.label("location_name"),
            ).join(Location, Attendance.location_id == Location.id)

            # 日付範囲が指定されている場合はフィルタを適用
            if start_date and end_date:
                query = query.filter(
                    Attendance.date >= start_date, Attendance.date <= end_date
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
        self,
        db: Session,
        *,
        month: Optional[str] = None,
        fiscal_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        勤怠集計用のデータを取得します。
        月別・年度別にユーザーごとの勤怠種別日数と日付一覧を返します。

        Args:
            db: データベースセッション
            month: 対象月（YYYY-MM形式、指定がない場合は現在の月）
            fiscal_year: 対象年度（4月開始）。指定された場合は年度優先。

        Returns:
            Dict[str, Any]: 分析データ
                - period: 集計期間情報（mode/label/start/endなど）
                - users: ユーザー別の勤怠データ（種別別日数・日付一覧）
                - locations: 勤怠種別一覧
                - group_summary: グループ別集計
                - summary: 全体サマリー
        """
        import calendar
        from datetime import date, datetime

        from sqlalchemy import and_

        from app.crud.location import location as location_crud
        from app.crud.user import user as user_crud

        try:
            if fiscal_year is not None:
                # 4月開始の年度
                period_mode = "fiscal_year"
                start_date = date(fiscal_year, 4, 1)
                end_date = date(fiscal_year + 1, 3, 31)
                period_label = f"{fiscal_year}年度"
                month_value: Optional[str] = None
            else:
                current_date = datetime.now()
                if month is None:
                    month = f"{current_date.year}-{current_date.month:02d}"
                year, month_num = map(int, month.split("-"))
                period_mode = "month"
                start_date = date(year, month_num, 1)
                end_date = date(
                    year, month_num, calendar.monthrange(year, month_num)[1]
                )
                period_label = f"{year}年{month_num}月"
                month_value = month

            # ユーザー情報を取得（グループ、ユーザー種別含む）
            users_data = user_crud.get_all_users_with_details(db)

            # 勤怠種別情報を取得
            locations = location_crud.get_multi(db)
            locations_sorted = sorted(
                locations, key=lambda x: (str(x.category or ""), x.order or 999, x.id)
            )

            # 対象期間の勤怠データを取得
            attendances = (
                db.query(Attendance)
                .filter(
                    and_(
                        Attendance.date >= start_date,
                        Attendance.date <= end_date,
                    )
                )
                .order_by(Attendance.date)
                .all()
            )

            # ユーザー別・勤怠種別別の日数を集計
            user_analysis: Dict[str, Dict[str, Any]] = {}
            location_totals = {
                int(loc.id): 0 for loc in locations_sorted if loc.id is not None
            }
            location_details: Dict[int, Dict[str, List[Dict[str, Any]]]] = {
                int(loc.id): {} for loc in locations_sorted if loc.id is not None
            }

            for user_name, user_id, group_name, user_type_name in users_data:
                user_attendances = [
                    att for att in attendances if att.user_id == user_id
                ]
                location_counts = {
                    int(loc.id): 0 for loc in locations_sorted if loc.id is not None
                }
                location_dates: Dict[int, List[Dict[str, Any]]] = {
                    int(loc.id): [] for loc in locations_sorted if loc.id is not None
                }

                for att in user_attendances:
                    location_counts[int(att.location_id)] += 1
                    location_totals[int(att.location_id)] += 1
                    date_info = {
                        "date_str": att.date.strftime("%Y-%m-%d"),
                        "date_jp": f"{att.date.month}月{att.date.day}日",
                        "date_mmdd": att.date.strftime("%m/%d"),
                        "date_simple": f"{att.date.month}/{att.date.day}",
                        "note": att.note or "",
                    }
                    location_dates[int(att.location_id)].append(date_info)

                # 日付を昇順に整列し、location_detailsにも格納
                for loc_id, dates in location_dates.items():
                    if dates:
                        sorted_dates = sorted(dates, key=lambda d: d["date_str"])
                        location_dates[int(loc_id)] = sorted_dates
                        location_details[int(loc_id)][str(user_id)] = sorted_dates

                total_days = sum(location_counts.values())

                user_analysis[user_id] = {
                    "user_name": user_name,
                    "group_name": group_name,
                    "user_type_name": user_type_name,
                    "location_counts": location_counts,
                    "location_dates": location_dates,
                    "total_days": total_days,
                }

            # 勤怠種別情報を整理
            locations_info: List[SimpleNamespace] = []
            for loc in locations_sorted:
                if loc.id is None:
                    continue
                locations_info.append(
                    SimpleNamespace(
                        id=loc.id,
                        name=loc.name,
                        category=loc.category,
                        order=loc.order,
                        total_days=location_totals[int(loc.id)],
                    )
                )

            # グループ別サマリー
            group_summary: Dict[str, Dict[str, Any]] = {}
            for _, user_id, group_name, _ in users_data:
                group_key = group_name or "未分類"
                if group_key not in group_summary:
                    group_summary[group_key] = {
                        "location_counts": {
                            int(loc.id): 0
                            for loc in locations_sorted
                            if loc.id is not None
                        },
                        "total_days": 0,
                    }
                user_counts = user_analysis.get(user_id, {}).get("location_counts", {})
                for loc_id, cnt in user_counts.items():
                    group_summary[group_key]["location_counts"][loc_id] += cnt
                    group_summary[group_key]["total_days"] += cnt

            total_users = len(user_analysis)
            total_attendance_days = sum(location_totals.values())

            return {
                "month": month_value or "",
                "month_name": period_label,
                "period": {
                    "mode": period_mode,
                    "label": period_label,
                    "start": start_date,
                    "end": end_date,
                    "fiscal_year": fiscal_year,
                    "month": month_value,
                },
                "users": user_analysis,
                "locations": locations_info,
                "group_summary": group_summary,
                "location_details": location_details,
                "summary": {
                    "total_users": total_users,
                    "total_attendance_days": total_attendance_days,
                    "location_totals": location_totals,
                },
            }

        except Exception as e:
            logger.error(
                f"勤怠集計データ取得中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {
                "month": month or "",
                "month_name": "エラー",
                "period": {
                    "mode": "error",
                    "label": "エラー",
                    "start": None,
                    "end": None,
                    "fiscal_year": fiscal_year,
                    "month": month,
                },
                "users": {},
                "locations": [],
                "group_summary": {},
                "location_details": {},
                "summary": {
                    "total_users": 0,
                    "total_attendance_days": 0,
                    "location_totals": {},
                },
            }

    def get_attendance_by_type_for_fiscal_year(
        self,
        db: Session,
        *,
        location_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        年度ベースで指定された勤怠種別の詳細データを取得します。
        ユーザーごとに、指定された勤怠種別が登録されている日付一覧を返します。

        Args:
            db: データベースセッション
            location_id: 勤怠種別ID（指定がない場合は最初の勤怠種別）
            year: 対象年度（指定がない場合は現在の年）

        Returns:
            Dict[str, Any]: 勤怠種別別詳細データ
                - year: 対象年
                - location_name: 勤怠種別名
                - users_data: ユーザー別の勤怠日付一覧
                - locations: 全勤怠種別一覧（ラジオボタン用）
        """
        from datetime import date, datetime

        from sqlalchemy import and_

        from app.crud.location import location as location_crud
        from app.crud.user import user as user_crud

        try:
            # 対象年の決定
            if year is None:
                year = datetime.now().year

            # 年度の開始日と終了日を計算（1月1日〜12月31日）
            first_day = date(year, 1, 1)
            last_day = date(year, 12, 31)

            # 勤怠種別情報を取得
            locations = location_crud.get_multi(db)
            locations_sorted = sorted(
                locations, key=lambda x: (x.category or "", x.order or 999, x.id)
            )

            # デフォルトの勤怠種別IDを設定
            if location_id is None and locations_sorted:
                location_id = int(locations_sorted[0].id)

            # 選択された勤怠種別の名前を取得
            selected_location = next(
                (loc for loc in locations_sorted if loc.id == location_id), None
            )
            location_name = selected_location.name if selected_location else "不明"

            # ユーザー情報を取得（グループ、ユーザー種別含む）
            users_data = user_crud.get_all_users_with_details(db)

            # 対象期間・勤怠種別の勤怠データを取得
            attendances = (
                db.query(Attendance)
                .filter(
                    and_(
                        Attendance.date >= first_day,
                        Attendance.date <= last_day,
                        Attendance.location_id == location_id,
                    )
                )
                .order_by(Attendance.date)
                .all()
            )

            # ユーザー別に勤怠日付をグループ化
            users_attendance_data = {}

            for user_data in users_data:
                user_name, user_id, group_name, user_type_name = user_data

                # このユーザーの勤怠データを抽出
                user_attendances = [
                    att for att in attendances if att.user_id == user_id
                ]

                # 日付一覧を作成
                attendance_dates = []
                for att in user_attendances:
                    attendance_dates.append(
                        {
                            "date": att.date,
                            "date_str": att.date.strftime("%Y-%m-%d"),
                            "date_jp": f"{att.date.month}月{att.date.day}日",
                            "date_mmdd": att.date.strftime("%m/%d"),
                            "date_simple": f"{att.date.month}/{att.date.day}",
                            "note": att.note or "",
                        }
                    )

                if attendance_dates:  # 勤怠データがある場合のみ追加
                    users_attendance_data[user_id] = {
                        "user_name": user_name,
                        "group_name": group_name,
                        "user_type_name": user_type_name,
                        "attendance_dates": attendance_dates,
                        "total_days": len(attendance_dates),
                    }

            # 勤怠種別情報を整理（ラジオボタン用）
            locations_info = []
            for loc in locations_sorted:
                locations_info.append(
                    {"id": loc.id, "name": loc.name, "category": loc.category}
                )

            return {
                "year": year,
                "location_id": location_id,
                "location_name": location_name,
                "users_data": users_attendance_data,
                "locations": locations_info,
                "total_users": len(users_attendance_data),
                "total_records": len(attendances),
            }

        except Exception as e:
            logger.error(
                f"勤怠種別別データ取得中にエラーが発生しました: {str(e)}", exc_info=True
            )
            return {
                "year": year or datetime.now().year,
                "location_id": location_id,
                "location_name": "エラー",
                "users_data": {},
                "locations": [],
                "total_users": 0,
                "total_records": 0,
            }


attendance = CRUDAttendance(Attendance)
