"""
Database service
==============

Service for database operations.
"""

import calendar
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.attendance import Attendance
from ..models.location import Location
from ..schemas.user import UserCreate
from ..schemas.attendance import AttendanceCreate
from ..schemas.location import LocationCreate
from ..utils.calendar_utils import parse_month, generate_location_data
from ..core.config import logger


# Calendar settings for Sunday as first day of week (0: Monday start → 6: Sunday start)
calendar.setfirstweekday(6)


def get_all_users(db: Session) -> List[Dict[str, Any]]:
    """すべてのユーザーを取得

    Args:
        db: Database session

    Returns:
        List[Dict[str, Any]]: ユーザーリスト
    """
    users = db.query(User).all()
    return [(user.username, user.user_id) for user in users]


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """ユーザーIDでユーザーを取得

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Optional[User]: 見つかったユーザー、または None
    """
    return db.query(User).filter(User.user_id == user_id).first()


def get_user_name_by_id(db: Session, user_id: str) -> str:
    """ユーザーIDからユーザー名を取得

    Args:
        db: Database session
        user_id: User ID

    Returns:
        str: ユーザー名（見つからない場合は空文字）
    """
    user = get_user_by_id(db, user_id)
    return user.username if user else ""


def add_user(db: Session, username: str, user_id: str) -> bool:
    """新しいユーザーを追加

    Args:
        db: Database session
        username: Username
        user_id: User ID

    Returns:
        bool: 成功したかどうか
    """
    try:
        # 既存ユーザーをチェック
        existing_user = get_user_by_id(db, user_id)
        if existing_user:
            return False

        # 新しいユーザーを作成
        user = User(username=username, user_id=user_id)
        db.add(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding user: {str(e)}")
        return False


def delete_user(db: Session, user_id: str) -> bool:
    """ユーザーを削除

    Args:
        db: Database session
        user_id: User ID

    Returns:
        bool: 成功したかどうか
    """
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            return False

        # 関連する出席レコードも削除
        db.query(Attendance).filter(Attendance.user_id == user.id).delete()

        # ユーザーを削除
        db.delete(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        return False


def update_user_entry(db: Session, user_id: str, date_str: str, location: str) -> bool:
    """ユーザーの出席情報を更新

    Args:
        db: Database session
        user_id: User ID
        date_str: Date string (YYYY-MM-DD)
        location: Location name

    Returns:
        bool: 成功したかどうか
    """
    try:
        # ユーザーを取得
        user = get_user_by_id(db, user_id)
        if not user:
            return False

        # 日付を変換
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return False

        # ロケーションを取得または作成
        db_location = db.query(Location).filter(Location.name == location).first()
        if not db_location:
            db_location = Location(name=location)
            db.add(db_location)

        # 既存の出席レコードを確認
        attendance = (
            db.query(Attendance)
            .filter(Attendance.user_id == user.id, Attendance.date == date_obj)
            .first()
        )

        if attendance:
            # 既存のレコードを更新
            attendance.location = location
        else:
            # 新しいレコードを作成
            attendance = Attendance(user_id=user.id, date=date_obj, location=location)
            db.add(attendance)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user entry: {str(e)}")
        return False


def get_day_data(db: Session, day: str) -> Dict[str, List[Dict[str, str]]]:
    """指定した日の全ユーザーの出席データを取得

    Args:
        db: Database session
        day: Date string (YYYY-MM-DD)

    Returns:
        Dict[str, List[Dict[str, str]]]: 勤務場所ごとにグループ化された出席データ
    """
    try:
        # 日付を変換
        try:
            date_obj = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date format: {day}")
            return {}

        # 指定した日の出席レコードを取得
        results = (
            db.query(Attendance, User)
            .join(User, Attendance.user_id == User.id)
            .filter(Attendance.date == date_obj)
            .all()
        )

        # 勤務場所ごとにユーザーをグループ化
        location_groups = {}
        for attendance, user in results:
            location = attendance.location
            if location not in location_groups:
                location_groups[location] = []

            location_groups[location].append(
                {
                    "user_name": user.username,
                    "user_id": user.user_id,
                }
            )

        return location_groups
    except Exception as e:
        logger.error(f"Error getting day data: {str(e)}")
        return {}


def get_location_types(db: Session) -> List[str]:
    """勤務場所の種類を取得

    Args:
        db: Database session

    Returns:
        List[str]: 勤務場所リスト
    """
    try:
        locations = db.query(Location).all()
        return [loc.name for loc in locations]
    except Exception as e:
        logger.error(f"Error getting location types: {str(e)}")
        return []


def get_user_data(db: Session, user_id: str) -> List[Dict[str, str]]:
    """ユーザーの全出席データを取得

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List[Dict[str, str]]: 出席データリスト
    """
    try:
        # ユーザーを取得
        user = get_user_by_id(db, user_id)
        if not user:
            return []

        # ユーザーの出席レコードを取得
        attendances = db.query(Attendance).filter(Attendance.user_id == user.id).all()

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
    except Exception as e:
        logger.error(f"Error getting user data: {str(e)}")
        return []


def get_calendar_data(db: Session, month: str) -> Dict[str, Any]:
    """指定された月のカレンダーデータを取得

    Args:
        db: Database session
        month: Month in YYYY-MM format

    Returns:
        Dict[str, Any]: Calendar data
    """
    try:
        year, month_num = parse_month(month)
        month_name = f"{year}年{month_num}月"

        # その月のカレンダーを作成
        cal = calendar.monthcalendar(year, month_num)

        # 勤務場所のリストを取得
        location_types = get_location_types(db)

        # 日ごとの勤務場所カウントを初期化
        location_counts = defaultdict(lambda: defaultdict(int))

        # 月の初日と末日を取得
        first_day = date(year, month_num, 1)
        last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

        # この月の全出席レコードを取得
        attendances = (
            db.query(Attendance)
            .filter(Attendance.date >= first_day, Attendance.date <= last_day)
            .all()
        )

        # 勤務場所ごとのカウントを集計
        for attendance in attendances:
            day = attendance.date.day
            location = attendance.location
            location_counts[day][location] += 1

        # 各週と日に出席情報を付与
        weeks = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:
                    # 月の範囲外の日
                    week_data.append({"day": 0, "date": "", "has_data": False})
                else:
                    current_date = date(year, month_num, day)
                    date_str = current_date.strftime("%Y-%m-%d")

                    # この日の出席データをカウント
                    attendance_count = (
                        db.query(Attendance)
                        .filter(Attendance.date == current_date)
                        .count()
                    )

                    day_data = {
                        "day": day,
                        "date": date_str,
                        "has_data": attendance_count > 0,
                    }

                    # 各勤務場所のカウントを追加
                    for loc_type in location_types:
                        day_data[loc_type] = location_counts[day].get(loc_type, 0)

                    week_data.append(day_data)
            weeks.append(week_data)

        # 前月と翌月の情報を計算
        prev_month_date = date(year, month_num, 1) - timedelta(days=1)
        prev_month = f"{prev_month_date.year}-{prev_month_date.month:02d}"

        next_month_date = date(year, month_num, 28)  # 月末を超えても翌月になる
        if next_month_date.month == month_num:  # まだ同じ月の場合は日付を増やす
            next_month_date = next_month_date.replace(
                day=calendar.monthrange(year, month_num)[1]
            ) + timedelta(days=1)
        next_month = f"{next_month_date.year}-{next_month_date.month:02d}"

        # 勤務場所の表示データを生成
        locations = generate_location_data(location_types)

        return {
            "month_name": month_name,
            "weeks": weeks,
            "locations": locations,
            "prev_month": prev_month,
            "next_month": next_month,
        }
    except Exception as e:
        logger.error(f"Error getting calendar data: {str(e)}")
        return {"month_name": "", "weeks": [], "locations": []}
