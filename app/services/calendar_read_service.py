"""カレンダー表示用のread modelを組み立てるservice。"""

import calendar as calendar_module
from datetime import date
from typing import Any, Dict, Literal, Optional, TypedDict

from sqlalchemy.orm import Session

from app.crud.calendar import calendar_crud
from app.crud.location import location as location_crud
from app.utils.calendar_utils import (
    build_calendar_data,
    format_date_jp,
    get_current_month_formatted,
    get_today_formatted,
    parse_month,
)
from app.utils.ui_utils import UNRESOLVED_LOCATION_TONE, get_location_tone

DayKind = Literal["holiday", "sunday", "saturday", "weekday"]
_WEEKDAY_LABELS = ("日", "月", "火", "水", "木", "金", "土")


class SummaryCalendarLocationViewModel(TypedDict):
    """月次summary calendarの勤怠種別表示contract。"""

    name: str
    key: str
    tone: int


class SummaryCalendarCategoryViewModel(TypedDict):
    """月次summary calendarのcategory表示contract。"""

    name: str
    locations: list[SummaryCalendarLocationViewModel]


class SummaryCalendarDayViewModel(TypedDict):
    """月次summary calendarの1日分の表示contract。"""

    day: int
    date: str
    has_data: bool
    holiday_name: str
    weekday_label: str
    day_kind: DayKind
    counts: Dict[str, int]


class MonthCalendarViewModel(TypedDict):
    """月次calendar templateが参照するsummary page contract。"""

    current_month: str
    month: str
    prev_month: str
    next_month: str
    categories: list[SummaryCalendarCategoryViewModel]
    days: list[SummaryCalendarDayViewModel]
    selected_date: str
    today_date: str


class DayDetailViewModel(TypedDict):
    """1日分の勤怠をgroup/社員種別へ編成したdetail contract。"""

    date_str: str
    date_jp: str
    organized_by_group: Dict[str, Dict[str, Any]]
    has_data: bool


def normalize_month(month: Optional[str]) -> str:
    """month queryをcanonicalな``YYYY-MM``へ正規化する。

    未指定時だけ現在月を補う。形式不正は空値へ握り潰さずparse errorをcallerへ伝え、routerが
    current monthへのredirect contractを適用できるようにする。
    """
    value = month or get_current_month_formatted()
    year, month_num = parse_month(value)
    return f"{year}-{month_num:02d}"


def _build_summary_calendar_presentation(
    calendar_data: Dict[str, Any], *, today_date: str
) -> tuple[
    list[SummaryCalendarCategoryViewModel],
    list[SummaryCalendarDayViewModel],
    str,
]:
    """raw calendar dataをdeterministicなtemplate-ready presentationへ変換する。"""
    grouped_locations: Dict[str, list[SummaryCalendarLocationViewModel]] = {}
    for raw_location in calendar_data.get("locations", []):
        category = str(raw_location.get("category") or "未分類")
        raw_tone = raw_location.get("tone")
        grouped_locations.setdefault(category, []).append(
            {
                "name": str(raw_location["name"]),
                "key": str(raw_location["key"]),
                "tone": (
                    int(raw_tone) if raw_tone is not None else UNRESOLVED_LOCATION_TONE
                ),
            }
        )

    categories: list[SummaryCalendarCategoryViewModel] = []
    for category in sorted(
        grouped_locations,
        key=lambda category: (category == "未分類", category),
    ):
        categories.append(
            {
                "name": category,
                "locations": grouped_locations[category],
            }
        )

    location_keys = [
        location["key"] for category in categories for location in category["locations"]
    ]

    days: list[SummaryCalendarDayViewModel] = []
    for week in calendar_data.get("weeks", []):
        for weekday_index, raw_day in enumerate(week):
            day_number = int(raw_day.get("day", 0) or 0)
            if day_number == 0:
                continue

            is_holiday = bool(raw_day.get("is_holiday", False))
            day_kind: DayKind
            if is_holiday:
                day_kind = "holiday"
            elif weekday_index == 0:
                day_kind = "sunday"
            elif weekday_index == 6:
                day_kind = "saturday"
            else:
                day_kind = "weekday"

            days.append(
                {
                    "day": day_number,
                    "date": str(raw_day["date"]),
                    "has_data": bool(raw_day.get("has_data", False)),
                    "holiday_name": str(raw_day.get("holiday_name") or ""),
                    "weekday_label": _WEEKDAY_LABELS[weekday_index],
                    "day_kind": day_kind,
                    "counts": {
                        key: int(raw_day.get(key, 0) or 0) for key in location_keys
                    },
                }
            )

    selected_date = days[0]["date"] if days else ""
    if any(day["date"] == today_date for day in days):
        selected_date = today_date

    return categories, days, selected_date


def get_month_view_model(
    db: Session, *, month: Optional[str] = None
) -> MonthCalendarViewModel:
    """月次summary calendarを共有DBのcurrent stateから毎回構築する。

    process-local DB result cacheは持たないため、commit後に開始した次readは別replicaのwriteも
    共有DBから観測できる。祝日判定はcaller側request dependencyが束縛したcustom holiday
    snapshotをcalendar utilityが参照する前提で、ここでは独自cacheを作らない。

    location metadataが集計結果と対応しない場合だけneutral toneへfallbackし、欠落した
    master rowを推測して作らない。category grouping、day metadata、selected dateまでこのserviceで
    決定し、templateへdeterministicなrender-ready contractを渡す。
    """
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
    locations = location_crud.list_all(db)
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
                    "tone": UNRESOLVED_LOCATION_TONE,
                    "category": None,
                    "order": None,
                }
            )
            continue

        location_data.update(
            {
                "tone": get_location_tone(int(location.id)),
                "category": location.category,
                "order": location.order,
            }
        )

    today_date = get_today_formatted()
    categories, days, selected_date = _build_summary_calendar_presentation(
        calendar_data,
        today_date=today_date,
    )

    return {
        "current_month": current_month,
        "month": str(calendar_data.get("month_name", "エラー")),
        "prev_month": str(calendar_data.get("prev_month", "")),
        "next_month": str(calendar_data.get("next_month", "")),
        "categories": categories,
        "days": days,
        "selected_date": selected_date,
        "today_date": today_date,
    }


def get_day_detail_view_model(db: Session, *, day: date) -> DayDetailViewModel:
    """日別detailをgroup/社員種別単位へ編成し、安定した表示順で返す。

    HTTP input validationはrouterが所有し、このserviceはvalidated dateだけを受け取る。groupは
    明示order、persistent ID、nameの順でsortし、``order=0`` と未設定を区別する。社員種別も
    order/ID/name、同一種別内のuserは表示名/IDでtie-breakするため、DB row返却順へ依存しない。
    """
    rows = calendar_crud.get_day_attendance_rows(db, target_date=day)
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
        location_tone = get_location_tone(int(row.location_id))

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
                "location_tone": location_tone,
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
        "date_str": day.isoformat(),
        "date_jp": format_date_jp(day),
        "organized_by_group": sorted_groups,
        "has_data": bool(rows),
    }
