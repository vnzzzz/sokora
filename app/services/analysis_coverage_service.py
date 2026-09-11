"""分析画面の組織・社員種別coverageをpresentation modelへ変換する。"""

from __future__ import annotations

import calendar as calendar_module
from datetime import date
from typing import Any, Dict, List, TypedDict

from app.services.analysis_read_service import GroupSection
from app.utils.ui_utils import get_location_tone


class CoverageLocation(TypedDict):
    """Coverage matrixで使う勤怠種別legend item。"""

    location_id: int
    name: str
    tone_index: int


class CoverageTypeCount(TypedDict):
    """Coverage cell内の勤怠種別別unique社員数。"""

    location_id: int
    name: str
    tone_index: int
    count: int


class CoverageCell(TypedDict):
    """1区分×1期間bucketのunique社員coverage。"""

    key: str
    label: str
    total: int
    type_counts: List[CoverageTypeCount]


class CoverageRow(TypedDict):
    """Coverage matrixの1行。"""

    label: str
    member_count: int
    cells: List[CoverageCell]


class AnalysisCoverageViewModel(TypedDict):
    """Coverage templateが参照するpresentation contract。"""

    coverage_locations: List[CoverageLocation]
    coverage_buckets: List[tuple[str, str]]
    group_coverage_rows: List[CoverageRow]
    user_type_coverage_rows: List[CoverageRow]


def _bucket_specs(
    analysis_data: Dict[str, Any],
    *,
    is_year_mode: bool,
) -> List[tuple[str, str]]:
    period_start = analysis_data["period"]["start"]
    if is_year_mode:
        specs: List[tuple[str, str]] = []
        start_month_index = period_start.year * 12 + period_start.month - 1
        for offset in range(12):
            month_index = start_month_index + offset
            bucket_year, month_zero_based = divmod(month_index, 12)
            bucket_month = month_zero_based + 1
            specs.append(
                (
                    f"{bucket_year:04d}-{bucket_month:02d}",
                    f"{bucket_month}月",
                )
            )
        return specs

    days_in_month = calendar_module.monthrange(
        period_start.year,
        period_start.month,
    )[1]
    return [
        (
            date(period_start.year, period_start.month, day).isoformat(),
            str(day),
        )
        for day in range(1, days_in_month + 1)
    ]


def _bucket_key(attendance_date: date, *, is_year_mode: bool) -> str:
    return (
        attendance_date.strftime("%Y-%m")
        if is_year_mode
        else attendance_date.isoformat()
    )


def _coverage_locations(
    analysis_data: Dict[str, Any],
    selected_location_ids: set[int],
) -> List[CoverageLocation]:
    return [
        {
            "location_id": int(location.id),
            "name": str(location.name),
            "tone_index": get_location_tone(int(location.id)),
        }
        for location in analysis_data.get("locations", [])
        if int(location.id) in selected_location_ids
    ]


def _row_names(
    group_sections: List[GroupSection],
) -> tuple[List[str], List[str]]:
    group_names = [section["name"] for section in group_sections]
    user_type_names: List[str] = []
    seen_user_types: set[str] = set()

    for group in group_sections:
        for user_type in group["user_types"]:
            name = user_type["name"]
            if name in seen_user_types:
                continue
            user_type_names.append(name)
            seen_user_types.add(name)

    return group_names, user_type_names


def _build_dimension_rows(
    analysis_data: Dict[str, Any],
    *,
    names: List[str],
    dimension_key: str,
    specs: List[tuple[str, str]],
    is_year_mode: bool,
    locations: List[CoverageLocation],
    selected_location_ids: set[int],
) -> List[CoverageRow]:
    users = analysis_data.get("users", {})
    location_details = analysis_data.get("location_details", {})
    location_ids = [location["location_id"] for location in locations]
    bucket_keys = {key for key, _ in specs}

    members: Dict[str, set[str]] = {name: set() for name in names}
    totals: Dict[str, Dict[str, set[str]]] = {
        name: {key: set() for key, _ in specs} for name in names
    }
    by_location: Dict[str, Dict[str, Dict[int, set[str]]]] = {
        name: {
            key: {location_id: set() for location_id in location_ids}
            for key, _ in specs
        }
        for name in names
    }

    for user_id, user_info in users.items():
        name = str(user_info.get(dimension_key) or "未分類")
        if name in members:
            members[name].add(str(user_id))

    for raw_location_id, details_by_user in location_details.items():
        location_id = int(raw_location_id)
        if location_id not in selected_location_ids:
            continue

        for user_id, date_details in details_by_user.items():
            user_id_str = str(user_id)
            user_info = users.get(user_id_str)
            if user_info is None:
                continue

            name = str(user_info.get(dimension_key) or "未分類")
            if name not in totals:
                continue

            for date_detail in date_details:
                attendance_date = date.fromisoformat(str(date_detail["date_str"]))
                key = _bucket_key(
                    attendance_date,
                    is_year_mode=is_year_mode,
                )
                if key not in bucket_keys:
                    continue

                totals[name][key].add(user_id_str)
                if location_id in by_location[name][key]:
                    by_location[name][key][location_id].add(user_id_str)

    rows: List[CoverageRow] = []
    for name in names:
        cells: List[CoverageCell] = []
        for key, label in specs:
            type_counts: List[CoverageTypeCount] = []
            for location in locations:
                location_id = location["location_id"]
                count = len(by_location[name][key][location_id])
                if count == 0:
                    continue
                type_counts.append(
                    {
                        "location_id": location_id,
                        "name": location["name"],
                        "tone_index": location["tone_index"],
                        "count": count,
                    }
                )

            cells.append(
                {
                    "key": key,
                    "label": label,
                    "total": len(totals[name][key]),
                    "type_counts": type_counts,
                }
            )

        rows.append(
            {
                "label": name,
                "member_count": len(members[name]),
                "cells": cells,
            }
        )

    return rows


def get_analysis_coverage_view_model(
    *,
    analysis_data: Dict[str, Any],
    group_sections: List[GroupSection],
    selected_location_ids: List[int],
    is_year_mode: bool,
) -> AnalysisCoverageViewModel:
    """同一read snapshotから組織別・社員種別別coverageを構築する。"""
    specs = _bucket_specs(
        analysis_data,
        is_year_mode=is_year_mode,
    )
    selected = {int(location_id) for location_id in selected_location_ids}
    locations = _coverage_locations(
        analysis_data,
        selected,
    )
    group_names, user_type_names = _row_names(group_sections)

    group_rows = _build_dimension_rows(
        analysis_data,
        names=group_names,
        dimension_key="group_name",
        specs=specs,
        is_year_mode=is_year_mode,
        locations=locations,
        selected_location_ids=selected,
    )
    user_type_rows = _build_dimension_rows(
        analysis_data,
        names=user_type_names,
        dimension_key="user_type_name",
        specs=specs,
        is_year_mode=is_year_mode,
        locations=locations,
        selected_location_ids=selected,
    )

    return {
        "coverage_locations": locations,
        "coverage_buckets": specs,
        "group_coverage_rows": group_rows,
        "user_type_coverage_rows": user_type_rows,
    }
