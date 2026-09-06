"""勤怠read projectionをpersistence queryから組み立てる。"""

import calendar
from datetime import date
from typing import Any, Dict, Optional, TypedDict

from sqlalchemy.orm import Session, joinedload

from app import crud, models
from app.crud.calendar import calendar_crud
from app.utils.calendar_utils import (
    build_calendar_data,
    build_week_calendar_data,
)
from app.utils.ui_utils import get_location_color_classes


UserViewRow = tuple[str, str, int, models.User]
UserTypeSection = tuple[float, str, list[UserViewRow]]


class AttendanceDirectoryViewModel(TypedDict):
    """weekly/monthly user directoryをtemplateへ渡すread contract。"""

    users: list[UserViewRow]
    grouped_users: dict[str, list[UserTypeSection]]
    group_names: list[str]
    search_query: Optional[str]


class WeeklyAttendanceViewModel(AttendanceDirectoryViewModel):
    """weekly attendance matrixのtemplate contract。"""

    calendar_data: list[list[dict[str, Any]]]
    week_name: str
    prev_week: str
    next_week: str
    current_week: str
    location_objects: list[models.Location]
    location_styles: dict[str, dict[str, str]]
    location_data_for_js: dict[int, str]
    user_attendances: dict[str, dict[str, bool]]
    user_attendance_locations: dict[str, dict[str, str]]
    user_attendance_notes: dict[str, dict[str, Optional[str]]]
    calendar_day_count: int


class MonthlyRegisterViewModel(AttendanceDirectoryViewModel):
    """monthly registerのuser list contract。"""

    current_month: str


class UserMonthlyCalendarViewModel(TypedDict):
    """1 user分のmonthly calendar partial contract。"""

    user: models.User
    calendar_data: list[list[dict[str, Any]]]
    month_name: str
    prev_month: str
    next_month: str
    current_month: str
    user_attendances: dict[str, dict[str, Any]]
    location_styles: dict[str, dict[str, str]]
    location_objects: list[models.Location]


def get_attendance_data_for_csv(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, str]:
    """CSV projection用にuser/date keyの勤怠種別mappingを返す。

    optionalな開始/終了日はpersistence queryへそのまま渡し、範囲外rowをservice側で再filter
    しない。1ユーザー1日1勤怠というDB unique contractを前提に1 keyへ1 valueだけを持つ。
    export readは共有DBのcurrent stateから毎回構築し、process-local cacheを作らない。
    """
    rows = crud.attendance.list_export_rows(
        db,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        f"{row.user_id}_{row.date.strftime('%Y-%m-%d')}": str(row.location_name)
        for row in rows
    }


def _optional_order_key(
    order: Optional[int],
    object_id: int,
    name: str,
) -> tuple[bool, int, int, str]:
    """nullable orderを末尾へ送り、ID/nameで表示順を安定化する。"""
    return (
        order is None,
        order if order is not None else 0,
        object_id,
        name,
    )


def _read_users(db: Session) -> list[models.User]:
    """group/user typeを同時loadし、template accessのN+1を防ぐ。"""
    return list(
        db.query(models.User)
        .options(
            joinedload(models.User.group),
            joinedload(models.User.user_type),
        )
        .all()
    )


def _filter_user_rows(
    users: list[models.User],
    *,
    search_query: Optional[str],
) -> list[UserViewRow]:
    search_term = (search_query or "").strip().lower()
    rows: list[UserViewRow] = []
    for user in users:
        user_name = str(user.username)
        user_id = str(user.id)
        if (
            search_term
            and search_term not in user_name.lower()
            and search_term not in user_id.lower()
        ):
            continue
        rows.append((user_name, user_id, int(user.user_type_id), user))
    return rows


def _group_user_rows(
    rows: list[UserViewRow],
) -> tuple[dict[str, list[UserTypeSection]], list[str]]:
    """group/user type/userの表示順を1箇所で決定する。"""
    grouped: dict[str, dict[str, list[UserViewRow]]] = {}
    group_sort_keys: dict[str, tuple[bool, int, int, str]] = {}
    user_type_sort_keys: dict[str, tuple[bool, int, int, str]] = {}
    user_type_display_orders: dict[str, float] = {}

    for row in rows:
        user = row[3]
        group = user.group
        user_type = user.user_type

        group_name = str(group.name) if group is not None else "未分類"
        group_id = int(group.id) if group is not None and group.id is not None else 0
        group_order = (
            int(group.order)
            if group is not None and group.order is not None
            else None
        )
        group_sort_keys.setdefault(
            group_name,
            _optional_order_key(group_order, group_id, group_name),
        )

        user_type_name = (
            str(user_type.name) if user_type is not None else "未分類"
        )
        user_type_id = (
            int(user_type.id)
            if user_type is not None and user_type.id is not None
            else 0
        )
        user_type_order = (
            int(user_type.order)
            if user_type is not None and user_type.order is not None
            else None
        )
        user_type_sort_keys.setdefault(
            user_type_name,
            _optional_order_key(user_type_order, user_type_id, user_type_name),
        )
        user_type_display_orders.setdefault(
            user_type_name,
            float(user_type_order)
            if user_type_order is not None
            else float("inf"),
        )

        grouped.setdefault(group_name, {}).setdefault(user_type_name, []).append(row)

    grouped_users: dict[str, list[UserTypeSection]] = {}
    for group_name, users_by_type in grouped.items():
        sections: list[UserTypeSection] = []
        for user_type_name in sorted(
            users_by_type,
            key=user_type_sort_keys.__getitem__,
        ):
            user_rows = users_by_type[user_type_name]
            user_rows.sort(key=lambda row: (row[0], row[1]))
            sections.append(
                (
                    user_type_display_orders[user_type_name],
                    user_type_name,
                    user_rows,
                )
            )
        grouped_users[group_name] = sections

    group_names = sorted(grouped_users, key=group_sort_keys.__getitem__)
    return grouped_users, group_names


def _directory_view_model(
    db: Session,
    *,
    search_query: Optional[str],
) -> AttendanceDirectoryViewModel:
    rows = _filter_user_rows(_read_users(db), search_query=search_query)
    grouped_users, group_names = _group_user_rows(rows)
    return {
        "users": rows,
        "grouped_users": grouped_users,
        "group_names": group_names,
        "search_query": search_query,
    }


def _attendance_counts(rows: list[models.Attendance]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for attendance in rows:
        day = int(attendance.date.day)
        counts[day] = counts.get(day, 0) + 1
    return counts


def _location_styles(
    locations: list[models.Location],
) -> dict[str, dict[str, str]]:
    return {
        str(location.name): get_location_color_classes(int(location.id))
        for location in locations
    }


def get_weekly_page_view_model(
    db: Session,
    *,
    week: str,
    search_query: Optional[str] = None,
) -> WeeklyAttendanceViewModel:
    """weekly attendance matrixを固定query数で組み立てる。

    user/group/user typeはrelationship eager-load済み1 query、location masterは1 query、
    対象週attendanceはlocation込み1 queryで取得する。user数に比例するqueryは発行しない。
    """
    monday = date.fromisoformat(week)
    attendances = calendar_crud.get_week_attendances(db, monday=monday)
    locations = crud.location.list_all(db)
    directory = _directory_view_model(db, search_query=search_query)

    location_names = sorted(str(location.name) for location in locations)
    calendar_data = build_week_calendar_data(
        week_str=week,
        attendances=attendances,
        attendance_counts=_attendance_counts(attendances),
        location_types=location_names,
    )

    visible_user_ids = {row[1] for row in directory["users"]}
    user_attendances = {user_id: {} for user_id in visible_user_ids}
    user_attendance_locations = {user_id: {} for user_id in visible_user_ids}
    user_attendance_notes = {user_id: {} for user_id in visible_user_ids}

    for attendance in attendances:
        user_id = str(attendance.user_id)
        if user_id not in visible_user_ids:
            continue
        date_str = attendance.date.isoformat()
        user_attendances[user_id][date_str] = True
        user_attendance_locations[user_id][date_str] = str(
            attendance.location_info.name
        )
        user_attendance_notes[user_id][date_str] = attendance.note

    calendar_day_count = sum(
        1
        for week_data in calendar_data["weeks"]
        for day_data in week_data
        if day_data and day_data.get("day", 0) != 0
    )

    return {
        **directory,
        "calendar_data": calendar_data["weeks"],
        "week_name": str(calendar_data["week_name"]),
        "prev_week": str(calendar_data["prev_week"]),
        "next_week": str(calendar_data["next_week"]),
        "current_week": week,
        "location_objects": locations,
        "location_styles": _location_styles(locations),
        "location_data_for_js": {
            int(location.id): str(location.name) for location in locations
        },
        "user_attendances": user_attendances,
        "user_attendance_locations": user_attendance_locations,
        "user_attendance_notes": user_attendance_notes,
        "calendar_day_count": calendar_day_count,
    }


def get_monthly_register_page_view_model(
    db: Session,
    *,
    month: str,
    search_query: Optional[str] = None,
) -> MonthlyRegisterViewModel:
    """monthly registerのuser listだけをreadし、不要なcalendar queryを発行しない。"""
    directory = _directory_view_model(db, search_query=search_query)
    return {
        **directory,
        "current_month": month,
    }


def get_user_monthly_calendar_view_model(
    db: Session,
    *,
    user_id: str,
    month: str,
) -> Optional[UserMonthlyCalendarViewModel]:
    """1 userのmonthly calendarをperiod-scoped queryで構築する。"""
    user = crud.user.get_user_with_details(db, id=user_id)
    if user is None:
        return None

    year, month_num = (int(value) for value in month.split("-"))
    first_day = date(year, month_num, 1)
    last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])
    attendances = crud.attendance.list_user_for_period(
        db,
        user_id=user_id,
        start_date=first_day,
        end_date=last_day,
    )
    locations = crud.location.list_all(db)
    location_names = sorted(str(location.name) for location in locations)

    calendar_data = build_calendar_data(
        month=month,
        attendances=attendances,
        attendance_counts=_attendance_counts(attendances),
        location_types=location_names,
    )
    user_attendances = {
        attendance.date.isoformat(): {
            "location_name": str(attendance.location_info.name),
            "attendance_id": attendance.id,
            "note": attendance.note,
        }
        for attendance in attendances
    }

    return {
        "user": user,
        "calendar_data": calendar_data["weeks"],
        "month_name": str(calendar_data["month_name"]),
        "prev_month": str(calendar_data["prev_month"]),
        "next_month": str(calendar_data["next_month"]),
        "current_month": month,
        "user_attendances": user_attendances,
        "location_styles": _location_styles(locations),
        "location_objects": locations,
    }
