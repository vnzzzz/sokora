"""
カレンダー操作
===============

カレンダーデータ操作機能を提供します。
"""

import calendar
from typing import Dict, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.attendance import Attendance
from app.core.config import logger


# 日曜日を週の最初の日として設定 (0: 月曜始まり → 6: 日曜始まり)
calendar.setfirstweekday(6)


class CRUDCalendar:
    """カレンダー関連のデータアクセス操作クラス"""

    def get_month_attendances(
        self, db: Session, *, first_day: date, last_day: date
    ) -> List[Attendance]:
        """
        指定した期間内の勤怠データを取得

        Args:
            db: データベースセッション
            first_day: 期間の開始日
            last_day: 期間の終了日

        Returns:
            List[Attendance]: 勤怠データのリスト
        """
        try:
            return (
                db.query(Attendance)
                .filter(Attendance.date >= first_day, Attendance.date <= last_day)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting month attendances: {str(e)}")
            return []

    def count_day_attendances(self, db: Session, *, target_date: date) -> int:
        """
        指定した日の勤怠データ数を取得

        Args:
            db: データベースセッション
            target_date: 対象日

        Returns:
            int: 勤怠データ数
        """
        try:
            return db.query(Attendance).filter(Attendance.date == target_date).count()
        except Exception as e:
            logger.error(f"Error counting day attendances: {str(e)}")
            return 0

    def get_month_attendance_counts(self, db: Session, *, first_day: date, last_day: date) -> Dict[int, int]:
        """
        月内の日付ごとの勤怠データ数を一括取得

        Args:
            db: データベースセッション
            first_day: 月の初日
            last_day: 月の末日

        Returns:
            Dict[int, int]: 日付の日部分をキー、勤怠データ数を値とする辞書
        """
        try:
            attendance_counts = {}
            attendance_counts_query = (
                db.query(
                    func.extract('day', Attendance.date).label('day'),
                    func.count('*').label('count')
                )
                .filter(
                    and_(
                        Attendance.date >= first_day,
                        Attendance.date <= last_day
                    )
                )
                .group_by(func.extract('day', Attendance.date))
                .all()
            )
            
            for day, count in attendance_counts_query:
                attendance_counts[int(day)] = count
                
            return attendance_counts
        except Exception as e:
            logger.error(f"Error getting month attendance counts: {str(e)}")
            return {}


calendar_crud = CRUDCalendar()
