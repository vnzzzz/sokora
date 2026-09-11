"""Analysis coverage chart presentation tests."""

from datetime import date
from types import SimpleNamespace
from typing import Any, Dict, List

from app.services import analysis_coverage_service
from app.services.analysis_coverage_service import CoverageChart, CoverageSeries
from app.services.analysis_read_service import GroupSection
from app.utils.ui_utils import get_location_tone


def _analysis_data(period_start: date = date(2031, 5, 1)) -> Dict[str, Any]:
    return {
        "period": {"start": period_start},
        "locations": [
            SimpleNamespace(id=1, name="Office"),
            SimpleNamespace(id=2, name="Remote"),
        ],
        "users": {
            "u1": {"group_name": "Design", "user_type_name": "Employee"},
            "u2": {"group_name": "Design", "user_type_name": "Contractor"},
            "u3": {"group_name": "Sales", "user_type_name": "Employee"},
        },
        "location_details": {
            1: {
                "u1": [
                    {"date_str": "2031-05-03"},
                    {"date_str": "2031-05-04"},
                ],
                "u2": [{"date_str": "2031-05-03"}],
            },
            2: {
                "u1": [{"date_str": "2031-05-03"}],
                "u3": [{"date_str": "2031-05-03"}],
            },
        },
    }


def _group_sections() -> List[GroupSection]:
    return [
        {
            "name": "Design",
            "user_types": [
                {"name": "Employee", "users": []},
                {"name": "Contractor", "users": []},
            ],
        },
        {
            "name": "Sales",
            "user_types": [{"name": "Employee", "users": []}],
        },
    ]


def _series_by_name(chart: CoverageChart, name: str) -> CoverageSeries:
    return next(series for series in chart["series"] if series["name"] == name)


def _counts_by_key(series: CoverageSeries) -> Dict[str, int]:
    return {point["key"]: point["count"] for point in series["points"]}


def test_month_chart_defaults_to_all_people() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[1, 2],
        is_year_mode=False,
    )

    assert len(view_model["coverage_buckets"]) == 31
    assert view_model["group_options"] == ["Design", "Sales"]
    assert view_model["user_type_options"] == ["Employee", "Contractor"]
    assert view_model["selected_group_name"] is None
    assert view_model["selected_user_type_name"] is None
    assert view_model["coverage_chart"]["label"] == "全グループ / 全社員種別"
    assert [item["name"] for item in view_model["coverage_locations"]] == [
        "Office",
        "Remote",
    ]
    assert view_model["coverage_locations"][0]["tone_index"] == get_location_tone(1)

    office = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Office"))
    remote = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Remote"))
    assert office["2031-05-03"] == 2
    assert office["2031-05-04"] == 1
    assert remote["2031-05-03"] == 2
    assert remote["2031-05-04"] == 0


def test_group_and_user_type_filters_are_independent_and_intersect() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[1, 2],
        is_year_mode=False,
        selected_group_name="Design",
        selected_user_type_name="Employee",
    )

    assert view_model["selected_group_name"] == "Design"
    assert view_model["selected_user_type_name"] == "Employee"
    assert view_model["coverage_chart"]["label"] == "Design / Employee"

    office = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Office"))
    remote = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Remote"))
    assert office["2031-05-03"] == 1
    assert office["2031-05-04"] == 1
    assert remote["2031-05-03"] == 1


def test_user_type_filter_can_span_all_groups() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[2],
        is_year_mode=False,
        selected_user_type_name="Employee",
    )

    assert view_model["coverage_chart"]["label"] == "全グループ / Employee"
    remote = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Remote"))
    assert remote["2031-05-03"] == 2


def test_total_series_deduplicates_people_across_attendance_types() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[],
        is_year_mode=False,
        include_total=True,
        selected_group_name="Design",
    )

    assert view_model["include_total"] is True
    assert view_model["coverage_locations"] == []

    total = _series_by_name(view_model["coverage_chart"], "全合計")
    total_counts = _counts_by_key(total)
    assert total["is_total"] is True
    assert [series["name"] for series in view_model["coverage_chart"]["series"]] == [
        "全合計"
    ]
    assert total_counts["2031-05-03"] == 2
    assert total_counts["2031-05-04"] == 1


def test_invalid_target_filter_falls_back_to_all() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[1],
        is_year_mode=False,
        selected_group_name="Missing",
        selected_user_type_name="Unknown",
    )

    assert view_model["selected_group_name"] is None
    assert view_model["selected_user_type_name"] is None
    assert view_model["coverage_chart"]["label"] == "全グループ / 全社員種別"


def test_year_chart_counts_unique_people_per_month() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(date(2031, 4, 1)),
        group_sections=_group_sections(),
        selected_location_ids=[1, 2],
        is_year_mode=True,
        selected_group_name="Design",
    )

    assert [label for _, label in view_model["coverage_buckets"]] == [
        "4月",
        "5月",
        "6月",
        "7月",
        "8月",
        "9月",
        "10月",
        "11月",
        "12月",
        "1月",
        "2月",
        "3月",
    ]

    office = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Office"))
    remote = _counts_by_key(_series_by_name(view_model["coverage_chart"], "Remote"))
    assert office["2031-04"] == 0
    assert office["2031-05"] == 2
    assert remote["2031-05"] == 1


def test_empty_selection_keeps_chart_without_series() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[],
        is_year_mode=False,
    )

    assert view_model["include_total"] is False
    assert view_model["coverage_locations"] == []
    assert view_model["coverage_chart"]["series"] == []
