"""分析画面のcoverageを単一chart向けpresentation modelへ変換する。"""

from __future__ import annotations

import calendar as calendar_module
from datetime import date
from typing import Any, Dict, List, Optional, TypedDict

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
    """1勤怠種別または全合計の時系列。"""

    location_id: int
    name: str
    tone_index: int
    is_total: bool
    points: List[CoveragePoint]


class CoverageChart(TypedDict):
    """選択中のグループ・社員種別に対応する単一時系列chart。"""

    label: str
    max_count: int
    series: List[CoverageSeries]


class AnalysisCoverageViewModel(TypedDict):
    """Coverage chart templateが参照するpresentation contract。"""

    include_total: bool
    coverage_locations: List[CoverageLocation]
    coverage_buckets: List[tuple[str, str]]
    group_options: List[str]
    user_type_options: List[str]
    selected_group_name: Optional[str]
    selected_user_type_name: Optional[str]
    coverage_chart: CoverageChart


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


def _filter_options(
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


def _normalize_selection(value: Optional[str], options: List[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized not in options:
        return None
    return normalized


def _chart_label(
    selected_group_name: Optional[str],
    selected_user_type_name: Optional[str],
) -> str:
    group_label = selected_group_name or "全グループ"
    user_type_label = selected_user_type_name or "全社員種別"
    return f"{group_label} / {user_type_label}"


def _matches_target(
    user_info: Dict[str, Any],
    *,
    selected_group_name: Optional[str],
    selected_user_type_name: Optional[str],
) -> bool:
    if selected_group_name is not None:
        group_name = str(user_info.get("group_name") or "未分類")
        if group_name != selected_group_name:
            return False
    if selected_user_type_name is not None:
        user_type_name = str(user_info.get("user_type_name") or "未分類")
        if user_type_name != selected_user_type_name:
            return False
    return True


def _build_chart(
    analysis_data: Dict[str, Any],
    *,
    specs: List[tuple[str, str]],
    is_year_mode: bool,
    locations: List[CoverageLocation],
    selected_location_ids: set[int],
    include_total: bool,
    selected_group_name: Optional[str],
    selected_user_type_name: Optional[str],
) -> CoverageChart:
    users = analysis_data.get("users", {})
    location_details = analysis_data.get("location_details", {})
    bucket_keys = {key for key, _ in specs}
    available_location_ids = {
        int(location.id) for location in analysis_data.get("locations", [])
    }

    counts: Dict[int, Dict[str, set[str]]] = {
        location["location_id"]: {key: set() for key, _ in specs}
        for location in locations
    }
    total_counts: Dict[str, set[str]] = {key: set() for key, _ in specs}

    for raw_location_id, details_by_user in location_details.items():
        location_id = int(raw_location_id)
        contributes_to_total = include_total and location_id in available_location_ids
        contributes_to_location = location_id in selected_location_ids
        if not contributes_to_total and not contributes_to_location:
            continue

        for user_id, date_details in details_by_user.items():
            user_id_str = str(user_id)
            user_info = users.get(user_id_str)
            if user_info is None or not _matches_target(
                user_info,
                selected_group_name=selected_group_name,
                selected_user_type_name=selected_user_type_name,
            ):
                continue

            for date_detail in date_details:
                attendance_date = date.fromisoformat(str(date_detail["date_str"]))
                key = _bucket_key(attendance_date, is_year_mode=is_year_mode)
                if key not in bucket_keys:
                    continue
                if contributes_to_total:
                    total_counts[key].add(user_id_str)
                if contributes_to_location and location_id in counts:
                    counts[location_id][key].add(user_id_str)

    series: List[CoverageSeries] = []
    max_count = 0

    if include_total:
        total_points: List[CoveragePoint] = [
            {
                "key": key,
                "label": label,
                "count": len(total_counts[key]),
            }
            for key, label in specs
        ]
        max_count = max(
            max_count,
            max((point["count"] for point in total_points), default=0),
        )
        series.append(
            {
                "location_id": 0,
                "name": "全合計",
                "tone_index": 0,
                "is_total": True,
                "points": total_points,
            }
        )

    for location in locations:
        location_id = location["location_id"]
        points: List[CoveragePoint] = [
            {
                "key": key,
                "label": label,
                "count": len(counts[location_id][key]),
            }
            for key, label in specs
        ]
        max_count = max(
            max_count,
            max((point["count"] for point in points), default=0),
        )
        series.append(
            {
                "location_id": location_id,
                "name": location["name"],
                "tone_index": location["tone_index"],
                "is_total": False,
                "points": points,
            }
        )

    return {
        "label": _chart_label(selected_group_name, selected_user_type_name),
        "max_count": max(max_count, 1),
        "series": series,
    }


def get_analysis_coverage_view_model(
    *,
    analysis_data: Dict[str, Any],
    group_sections: List[GroupSection],
    selected_location_ids: List[int],
    is_year_mode: bool,
    include_total: bool = False,
    selected_group_name: Optional[str] = None,
    selected_user_type_name: Optional[str] = None,
) -> AnalysisCoverageViewModel:
    """同一read snapshotから選択中の対象だけを単一chartへ集約する。"""
    specs = _bucket_specs(
        analysis_data,
        is_year_mode=is_year_mode,
    )
    selected = {int(location_id) for location_id in selected_location_ids}
    locations = _coverage_locations(
        analysis_data,
        selected,
    )
    group_options, user_type_options = _filter_options(group_sections)
    normalized_group_name = _normalize_selection(
        selected_group_name,
        group_options,
    )
    normalized_user_type_name = _normalize_selection(
        selected_user_type_name,
        user_type_options,
    )
    chart = _build_chart(
        analysis_data,
        specs=specs,
        is_year_mode=is_year_mode,
        locations=locations,
        selected_location_ids=selected,
        include_total=include_total,
        selected_group_name=normalized_group_name,
        selected_user_type_name=normalized_user_type_name,
    )

    return {
        "include_total": include_total,
        "coverage_locations": locations,
        "coverage_buckets": specs,
        "group_options": group_options,
        "user_type_options": user_type_options,
        "selected_group_name": normalized_group_name,
        "selected_user_type_name": normalized_user_type_name,
        "coverage_chart": chart,
    }
