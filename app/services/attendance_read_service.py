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
from app.utils.ui_utils import get_location_tone

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
    location_tones: dict[str, int]
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
    location_tones: dict[str, int]
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

    Args:
        db: DB session。
        start_date: optionalなinclusive開始日。
        end_date: optionalなinclusive終了日。

    Returns:
        `user_id_YYYY-MM-DD`をkey、勤怠種別名をvalueとするmapping。
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
    """nullable orderを末尾へ送り、ID/nameで表示順を安定化する。

    Args:
        order: optionalな明示表示順。
        object_id: stable tie-break用persistent ID。
        name: 最終tie-break用表示名。

    Returns:
        未設定orderを末尾へ送るdeterministic sort key。
    """
    return (
        order is None,
        order if order is not None else 0,
        object_id,
        name,
    )


def _read_users(db: Session) -> list[models.User]:
    """group/user typeを同時loadして全userを取得する。

    Args:
        db: DB session。

    Returns:
        group/user type relationをeager-loadしたuser list。
    """
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
    """user一覧をname/ID検索し、template用rowへ変換する。

    Args:
        users: relationをload済みのuser list。
        search_query: optionalなname/ID検索文字列。

    Returns:
        検索条件に一致したtemplate用user row list。
    """
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
    """user rowをgroup/user type単位へ編成し表示順を決定する。

    Args:
        rows: template用user row list。

    Returns:
        group別user type section mappingと、表示順に並べたgroup名list。
    """
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
            int(group.order) if group is not None and group.order is not None else None
        )
        group_sort_keys.setdefault(
            group_name,
            _optional_order_key(group_order, group_id, group_name),
        )

        user_type_name = str(user_type.name) if user_type is not None else "未分類"
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
            float(user_type_order) if user_type_order is not None else float("inf"),
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
    """weekly/monthly共通のuser directory view modelを構築する。

    Args:
        db: DB session。
        search_query: optionalなname/ID検索文字列。

    Returns:
        user row、group編成、検索条件を含むdirectory view model。
    """
    rows = _filter_user_rows(_read_users(db), search_query=search_query)
    grouped_users, group_names = _group_user_rows(rows)
    return {
        "users": rows,
        "grouped_users": grouped_users,
        "group_names": group_names,
        "search_query": search_query,
    }


def _attendance_counts(rows: list[models.Attendance]) -> dict[int, int]:
    """勤怠recordを月内の日番号ごとの件数へ集計する。

    Args:
        rows: 集計対象の勤怠record list。

    Returns:
        日番号をkey、件数をvalueとするmapping。
    """
    counts: dict[int, int] = {}
    for attendance in rows:
        day = int(attendance.date.day)
        counts[day] = counts.get(day, 0) + 1
    return counts


def _location_tones(locations: list[models.Location]) -> dict[str, int]:
    """DB identityをpresentation-neutralなpalette slotへ射影する。

    Args:
        locations: 勤怠種別model list。

    Returns:
        勤怠種別名をkey、stable tone indexをvalueとするmapping。
    """
    return {
        str(location.name): get_location_tone(int(location.id))
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

    Args:
        db: DB session。
        week: 対象週の月曜日。ISO date文字列。
        search_query: optionalなname/ID検索文字列。

    Returns:
        weekly attendance matrix用のrender-ready view model。

    Raises:
        ValueError: `week`がISO dateとして解釈できない場合。
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
    user_attendances: dict[str, dict[str, bool]] = {
        user_id: {} for user_id in visible_user_ids
    }
    user_attendance_locations: dict[str, dict[str, str]] = {
        user_id: {} for user_id in visible_user_ids
    }
    user_attendance_notes: dict[str, dict[str, Optional[str]]] = {
        user_id: {} for user_id in visible_user_ids
    }

    for attendance in attendances:
        user_id = str(attendance.user_id)
        if user_id not in visible_user_ids:
            continue
        date_str = attendance.date.isoformat()
        user_attendances[user_id][date_str] = True
        user_attendance_locations[user_id][date_str] = str(
            attendance.location_info.name
        )
        user_attendance_notes[user_id][date_str] = (
            None if attendance.note is None else str(attendance.note)
        )

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
        "location_tones": _location_tones(locations),
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
    """monthly registerのuser listだけをreadする。

    calendar queryを発行せず、directoryとcurrent monthだけを返す。

    Args:
        db: DB session。
        month: 表示対象月のcanonical `YYYY-MM`文字列。
        search_query: optionalなname/ID検索文字列。

    Returns:
        monthly register user-list用view model。
    """
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
    """1 userのmonthly calendarをperiod-scoped queryで構築する。

    Args:
        db: DB session。
        user_id: 表示対象user ID。
        month: `YYYY-MM`形式の対象月。

    Returns:
        user monthly calendar用view model。userが存在しない場合は`None`。

    Raises:
        ValueError: `month`が有効な`YYYY-MM`として解釈できない場合。
    """
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
        "location_tones": _location_tones(locations),
        "location_objects": locations,
    }
