"""カレンダー表示用のread modelを組み立てるservice。"""

import calendar as calendar_module
from datetime import date
from typing import Any, Dict, Optional, TypedDict

from sqlalchemy.orm import Session

from app.crud.calendar import calendar_crud
from app.utils.calendar_utils import (
    build_calendar_data,
    format_date_jp,
    get_current_month_formatted,
    get_today_formatted,
    parse_date,
    parse_month,
)
from app.utils.ui_utils import get_location_color_classes


class MonthCalendarViewModel(TypedDict):
    current_month: str
    month: str
    calendar: Dict[str, Any]
    today_date: str


class DayDetailViewModel(TypedDict):
    date_str: str
    date_jp: str
    organized_by_group: Dict[str, Dict[str, Any]]
    has_data: bool


def normalize_month(month: Optional[str]) -> str:
    """month queryをYYYY-MMへ正規化する。"""
    value = month or get_current_month_formatted()
    year, month_num = parse_month(value)
    return f"{year}-{month_num:02d}"


def get_empty_month_view_model(month: Optional[str]) -> MonthCalendarViewModel:
    """月パラメータ解析失敗時に既存UI向けの空view modelを返す。"""
    current_month = month or get_current_month_formatted()
    return {
        "current_month": current_month,
        "month": "エラー",
        "calendar": {
            "weeks": [],
            "locations": [],
            "month_name": "エラー",
            "prev_month": current_month,
            "next_month": current_month,
        },
        "today_date": get_today_formatted(),
    }


def get_month_view_model(
    db: Session, *, month: Optional[str] = None
) -> MonthCalendarViewModel:
    """月次summary calendarの表示データをDBから毎回構築する。"""
    current_month = normalize_month(month)
    year, month_num = parse_month(current_month)
    first_day = date(year, month_num, 1)
    last_day = date(year, month_num, calendar_module.monthrange(year, month_num)[1])

    attendances = calendar_crud.get_month_attendances(
        db,
        first_day=first_day,
        last_day=last_day,
    )
    attendance_counts = calendar_crud.get_month_attendance_counts(
        db,
        first_day=first_day,
        last_day=last_day,
    )
    locations = calendar_crud.list_locations(db)
    location_names = [str(location.name) for location in locations]

    calendar_data = build_calendar_data(
        month=current_month,
        attendances=attendances,
        attendance_counts=attendance_counts,
        location_types=location_names,
    )

    locations_by_name = {str(location.name): location for location in locations}
    for location_data in calendar_data.get("locations", []):
        location = locations_by_name.get(str(location_data["name"]))
        if location is None:
            location_data.update(
                {
                    "text_class": "text-gray",
                    "bg_class": "bg-gray/15",
                    "category": None,
                    "order": None,
                }
            )
            continue

        color_info = get_location_color_classes(int(location.id))
        location_data.update(
            {
                "text_class": color_info["text_class"],
                "bg_class": color_info["bg_class"],
                "category": location.category,
                "order": location.order,
            }
        )

    return {
        "current_month": current_month,
        "month": str(calendar_data.get("month_name", "エラー")),
        "calendar": calendar_data,
        "today_date": get_today_formatted(),
    }


def get_day_detail_view_model(db: Session, *, day: str) -> DayDetailViewModel:
    """日別詳細をgroup/user type単位へ編成する。"""
    target_date = parse_date(day)
    if target_date is None:
        return {
            "date_str": day,
            "date_jp": "",
            "organized_by_group": {},
            "has_data": False,
        }

    rows = calendar_crud.get_day_attendance_rows(db, target_date=target_date)
    organized_by_group: Dict[str, Dict[str, Any]] = {}
    user_type_sort_info: Dict[str, tuple[int, int, str]] = {}

    for row in rows:
        group_name = str(row.group_name or "未分類")
        user_type_name = str(row.user_type_name or "未分類")
        group_id = int(row.group_id) if row.group_id is not None else 9999
        group_order = int(row.group_order) if row.group_order is not None else None
        user_type_id = int(row.user_type_id) if row.user_type_id is not None else 9999
        user_type_order = (
            int(row.user_type_order) if row.user_type_order is not None else 9999
        )
        color_info = get_location_color_classes(int(row.location_id))

        group_data = organized_by_group.setdefault(
            group_name,
            {
                "user_types": set(),
                "user_types_data": {},
                "group_id": group_id,
                "group_order": group_order,
            },
        )
        group_data["user_types"].add(user_type_name)
        group_data["user_types_data"].setdefault(user_type_name, []).append(
            {
                "user_name": str(row.user_name),
                "user_id": str(row.user_id),
                "user_type_id": user_type_id,
                "user_type_name": user_type_name,
                "group_id": str(group_id),
                "group_name": group_name,
                "note": row.note,
                "location_name": str(row.location_name),
                "location_text_class": color_info["text_class"],
                "location_bg_class": color_info["bg_class"],
            }
        )
        user_type_sort_info[user_type_name] = (
            user_type_order,
            user_type_id,
            user_type_name,
        )

    for group_data in organized_by_group.values():
        user_types = sorted(
            group_data["user_types"],
            key=lambda name: user_type_sort_info.get(name, (9999, 9999, name)),
        )
        group_data["user_types"] = user_types
        for user_list in group_data["user_types_data"].values():
            user_list.sort(
                key=lambda user_data: (
                    str(user_data["user_name"]),
                    str(user_data["user_id"]),
                )
            )

    sorted_groups = dict(
        sorted(
            organized_by_group.items(),
            key=lambda item: (
                item[1]["group_order"] is None,
                int(item[1]["group_order"])
                if item[1]["group_order"] is not None
                else 0,
                int(item[1]["group_id"]),
                item[0],
            ),
        )
    )

    return {
        "date_str": day,
        "date_jp": format_date_jp(target_date),
        "organized_by_group": sorted_groups,
        "has_data": bool(rows),
    }
