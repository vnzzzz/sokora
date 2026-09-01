"""Analysis page presentation read model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session

from app import crud
from app.services import attendance_analysis_service


class LocationCell(TypedDict):
    location_id: int
    count: int


class DateGroup(TypedDict):
    location_id: int
    location_name: str
    dates: List[Dict[str, Any]]


class AnalysisUserRow(TypedDict):
    user_id: str
    user_name: str
    group_name: str
    user_type_name: str
    location_cells: List[LocationCell]
    total_days: int
    date_groups: List[DateGroup]


class UserTypeSection(TypedDict):
    name: str
    users: List[AnalysisUserRow]


class GroupSection(TypedDict):
    name: str
    user_types: List[UserTypeSection]


class LocationCategory(TypedDict):
    name: str
    locations: List[Any]


class AnalysisPageViewModel(TypedDict):
    analysis_data: Dict[str, Any]
    is_year_mode: bool
    current_month: str
    current_year: int
    year_options: List[int]
    location_categories: List[LocationCategory]
    group_sections: List[GroupSection]
    location_details: Dict[int, Dict[str, List[Dict[str, Any]]]]
    empty_message: str


def _fiscal_year(today: date) -> int:
    return today.year if today.month >= 4 else today.year - 1


def _optional_order_key(
    order: Optional[int],
    object_id: int,
    name: str,
) -> tuple[bool, int, int, str]:
    return (
        order is None,
        order if order is not None else 0,
        object_id,
        name,
    )


def _location_category_name(location: Any) -> str:
    category = str(location.category or "").strip()
    return category or "未分類"


def _sort_locations(locations: List[Any]) -> List[Any]:
    return sorted(
        locations,
        key=lambda location: (
            _location_category_name(location) == "未分類",
            _location_category_name(location),
            location.order is None,
            int(location.order) if location.order is not None else 0,
            int(location.id),
            str(location.name),
        ),
    )


def _build_location_categories(locations: List[Any]) -> List[LocationCategory]:
    categories: Dict[str, List[Any]] = {}
    for location in locations:
        categories.setdefault(_location_category_name(location), []).append(location)

    category_names = sorted(
        categories,
        key=lambda name: (name == "未分類", name),
    )
    return [
        {"name": category_name, "locations": categories[category_name]}
        for category_name in category_names
    ]


def _build_group_sections(
    db: Session,
    *,
    analysis_data: Dict[str, Any],
    locations: List[Any],
) -> List[GroupSection]:
    group_sort_info: Dict[str, tuple[bool, int, int, str]] = {}
    for group in crud.group.get_multi(db):
        if group.id is None:
            continue
        name = str(group.name)
        order = int(group.order) if group.order is not None else None
        group_sort_info[name] = _optional_order_key(order, int(group.id), name)

    user_type_sort_info: Dict[str, tuple[bool, int, int, str]] = {}
    for user_type in crud.user_type.get_multi(db):
        if user_type.id is None:
            continue
        name = str(user_type.name)
        order = int(user_type.order) if user_type.order is not None else None
        user_type_sort_info[name] = _optional_order_key(
            order,
            int(user_type.id),
            name,
        )

    location_details = analysis_data.get("location_details", {})
    grouped: Dict[str, Dict[str, List[AnalysisUserRow]]] = {}

    for user_id, user_info in analysis_data.get("users", {}).items():
        group_name = str(user_info.get("group_name") or "未分類")
        user_type_name = str(user_info.get("user_type_name") or "未分類")
        user_id_str = str(user_id)

        location_cells: List[LocationCell] = []
        date_groups: List[DateGroup] = []
        for location in locations:
            location_id = int(location.id)
            count = int(user_info.get("location_counts", {}).get(location_id, 0))
            location_cells.append({"location_id": location_id, "count": count})

            dates = location_details.get(location_id, {}).get(user_id_str, [])
            if dates:
                date_groups.append(
                    {
                        "location_id": location_id,
                        "location_name": str(location.name),
                        "dates": dates,
                    }
                )

        row: AnalysisUserRow = {
            "user_id": user_id_str,
            "user_name": str(user_info.get("user_name") or ""),
            "group_name": group_name,
            "user_type_name": user_type_name,
            "location_cells": location_cells,
            "total_days": int(user_info.get("total_days") or 0),
            "date_groups": date_groups,
        }
        grouped.setdefault(group_name, {}).setdefault(user_type_name, []).append(row)

    group_sections: List[GroupSection] = []
    for group_name in sorted(
        grouped,
        key=lambda name: group_sort_info.get(name, (True, 0, 0, name)),
    ):
        user_types: List[UserTypeSection] = []
        users_by_type = grouped[group_name]
        for user_type_name in sorted(
            users_by_type,
            key=lambda name: user_type_sort_info.get(name, (True, 0, 0, name)),
        ):
            rows = sorted(
                users_by_type[user_type_name],
                key=lambda row: (row["user_name"], row["user_id"]),
            )
            user_types.append({"name": user_type_name, "users": rows})
        group_sections.append({"name": group_name, "user_types": user_types})

    return group_sections


def get_analysis_page_view_model(
    db: Session,
    *,
    month: Optional[str] = None,
    year: Optional[int] = None,
    mode: Optional[str] = None,
    today: Optional[date] = None,
) -> AnalysisPageViewModel:
    today_value = today or datetime.now().date()
    fiscal_default = _fiscal_year(today_value)
    is_year_mode = year is not None or mode == "year"

    if is_year_mode:
        target_fiscal_year = year if year is not None else fiscal_default
        analysis_data = attendance_analysis_service.get_attendance_analysis_data(
            db,
            fiscal_year=target_fiscal_year,
        )
    else:
        month_value = month or today_value.strftime("%Y-%m")
        analysis_data = attendance_analysis_service.get_attendance_analysis_data(
            db,
            month=month_value,
        )

    locations = _sort_locations(list(analysis_data.get("locations", [])))
    analysis_data = dict(analysis_data)
    analysis_data["locations"] = locations

    current_month = str(
        analysis_data["period"].get("month") or today_value.strftime("%Y-%m")
    )
    current_year = int(analysis_data["period"].get("fiscal_year") or fiscal_default)
    year_options = list(range(fiscal_default - 3, fiscal_default + 4))
    location_categories = _build_location_categories(locations)
    group_sections = _build_group_sections(
        db,
        analysis_data=analysis_data,
        locations=locations,
    )

    if is_year_mode:
        empty_message = f"{current_year}年度の勤怠データがありません。"
    else:
        empty_message = f"{analysis_data['month_name']}の勤怠データがありません。"

    return {
        "analysis_data": analysis_data,
        "is_year_mode": is_year_mode,
        "current_month": current_month,
        "current_year": current_year,
        "year_options": year_options,
        "location_categories": location_categories,
        "group_sections": group_sections,
        "location_details": analysis_data.get("location_details", {}),
        "empty_message": empty_message,
    }


def get_error_page_view_model(
    *,
    month: Optional[str] = None,
    today: Optional[date] = None,
) -> AnalysisPageViewModel:
    today_value = today or datetime.now().date()
    fiscal_default = _fiscal_year(today_value)
    current_month = month or ""

    analysis_data: Dict[str, Any] = {
        "month": current_month,
        "month_name": "エラー",
        "period": {
            "mode": "error",
            "label": "エラー",
            "start": None,
            "end": None,
            "fiscal_year": None,
            "month": current_month,
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

    return {
        "analysis_data": analysis_data,
        "is_year_mode": False,
        "current_month": current_month,
        "current_year": fiscal_default,
        "year_options": list(range(fiscal_default - 3, fiscal_default + 4)),
        "location_categories": [],
        "group_sections": [],
        "location_details": {},
        "empty_message": "エラー",
    }
