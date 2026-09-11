"""分析画面の組織・社員種別coverageをchart向けpresentation modelへ変換する。"""

from __future__ import annotations

import calendar as calendar_module
from datetime import date
from typing import Any, Dict, List, TypedDict

from app.services.analysis_read_service import GroupSection
from app.utils.ui_utils import get_location_tone


class CoverageLocation(TypedDict):
    """Chart legendで使う勤怠種別。"""

    location_id: int
    name: str
    tone_index: int


class CoveragePoint(TypedDict):
    """1勤怠種別×1期間bucketのunique社員数。"""

    key: str
    label: str
    count: int


class CoverageSeries(TypedDict):
    """1勤怠種別の時系列。"""

    location_id: int
    name: str
    tone_index: int
    points: List[CoveragePoint]


class CoverageChart(TypedDict):
    """1組織または1社員種別の時系列chart。"""

    label: str
    member_count: int
    series: List[CoverageSeries]


class AnalysisCoverageViewModel(TypedDict):
    """Coverage chart templateが参照するpresentation contract。"""

    coverage_locations: List[CoverageLocation]
    coverage_buckets: List[tuple[str, str]]
    group_coverage_charts: List[CoverageChart]
    user_type_coverage_charts: List[CoverageChart]


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
    if is_year_mode:
        return attendance_date.strftime("%Y-%m")
    return attendance_date.isoformat()


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


def _build_dimension_charts(
    analysis_data: Dict[str, Any],
    *,
    names: List[str],
    dimension_key: str,
    specs: List[tuple[str, str]],
    is_year_mode: bool,
    locations: List[CoverageLocation],
    selected_location_ids: set[int],
) -> List[CoverageChart]:
    users = analysis_data.get("users", {})
    location_details = analysis_data.get("location_details", {})
    bucket_keys = {key for key, _ in specs}

    members: Dict[str, set[str]] = {name: set() for name in names}
    counts: Dict[str, Dict[int, Dict[str, set[str]]]] = {
        name: {
            location["location_id"]: {key: set() for key, _ in specs}
            for location in locations
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
            if name not in counts or location_id not in counts[name]:
                continue

            for date_detail in date_details:
                attendance_date = date.fromisoformat(str(date_detail["date_str"]))
                key = _bucket_key(attendance_date, is_year_mode=is_year_mode)
                if key in bucket_keys:
                    counts[name][location_id][key].add(user_id_str)

    charts: List[CoverageChart] = []
    for name in names:
        series: List[CoverageSeries] = []
        for location in locations:
            location_id = location["location_id"]
            points: List[CoveragePoint] = [
                {
                    "key": key,
                    "label": label,
                    "count": len(counts[name][location_id][key]),
                }
                for key, label in specs
            ]
            series.append(
                {
                    "location_id": location_id,
                    "name": location["name"],
                    "tone_index": location["tone_index"],
                    "points": points,
                }
            )

        charts.append(
            {
                "label": name,
                "member_count": len(members[name]),
                "series": series,
            }
        )

    return charts


def get_analysis_coverage_view_model(
    *,
    analysis_data: Dict[str, Any],
    group_sections: List[GroupSection],
    selected_location_ids: List[int],
    is_year_mode: bool,
) -> AnalysisCoverageViewModel:
    """同一read snapshotから組織別・社員種別別の時系列を構築する。"""
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

    group_charts = _build_dimension_charts(
        analysis_data,
        names=group_names,
        dimension_key="group_name",
        specs=specs,
        is_year_mode=is_year_mode,
        locations=locations,
        selected_location_ids=selected,
    )
    user_type_charts = _build_dimension_charts(
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
        "group_coverage_charts": group_charts,
        "user_type_coverage_charts": user_type_charts,
    }
