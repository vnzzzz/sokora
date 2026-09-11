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


def _chart_by_label(charts: List[CoverageChart], label: str) -> CoverageChart:
    return next(chart for chart in charts if chart["label"] == label)


def _series_by_name(chart: CoverageChart, name: str) -> CoverageSeries:
    return next(series for series in chart["series"] if series["name"] == name)


def _counts_by_key(series: CoverageSeries) -> Dict[str, int]:
    return {point["key"]: point["count"] for point in series["points"]}


def test_month_charts_count_unique_people_per_work_type() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[1, 2],
        is_year_mode=False,
    )

    assert len(view_model["coverage_buckets"]) == 31
    assert [item["name"] for item in view_model["coverage_locations"]] == [
        "Office",
        "Remote",
    ]
    assert view_model["coverage_locations"][0]["tone_index"] == get_location_tone(1)

    design = _chart_by_label(view_model["group_coverage_charts"], "Design")
    sales = _chart_by_label(view_model["group_coverage_charts"], "Sales")
    design_office = _counts_by_key(_series_by_name(design, "Office"))
    design_remote = _counts_by_key(_series_by_name(design, "Remote"))
    sales_remote = _counts_by_key(_series_by_name(sales, "Remote"))

    assert design["member_count"] == 2
    assert design_office["2031-05-03"] == 2
    assert design_office["2031-05-04"] == 1
    assert design_remote["2031-05-03"] == 1
    assert design_remote["2031-05-04"] == 0
    assert sales_remote["2031-05-03"] == 1

    employee = _chart_by_label(
        view_model["user_type_coverage_charts"],
        "Employee",
    )
    contractor = _chart_by_label(
        view_model["user_type_coverage_charts"],
        "Contractor",
    )
    employee_remote = _counts_by_key(_series_by_name(employee, "Remote"))
    contractor_office = _counts_by_key(_series_by_name(contractor, "Office"))
    assert employee_remote["2031-05-03"] == 2
    assert contractor_office["2031-05-03"] == 1


def test_selected_work_type_exposes_zero_as_chart_point() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[2],
        is_year_mode=False,
    )

    design = _chart_by_label(view_model["group_coverage_charts"], "Design")
    remote = _counts_by_key(_series_by_name(design, "Remote"))

    assert remote["2031-05-03"] == 1
    assert remote["2031-05-04"] == 0
    assert view_model["coverage_locations"][0]["name"] == "Remote"


def test_year_charts_count_unique_people_per_month_and_work_type() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(date(2031, 4, 1)),
        group_sections=_group_sections(),
        selected_location_ids=[1, 2],
        is_year_mode=True,
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

    design = _chart_by_label(view_model["group_coverage_charts"], "Design")
    office = _counts_by_key(_series_by_name(design, "Office"))
    remote = _counts_by_key(_series_by_name(design, "Remote"))
    assert office["2031-04"] == 0
    assert office["2031-05"] == 2
    assert remote["2031-05"] == 1


def test_empty_selection_keeps_chart_groups_without_series() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[],
        is_year_mode=False,
    )

    assert view_model["coverage_locations"] == []
    assert all(
        chart["series"] == []
        for chart in view_model["group_coverage_charts"]
    )
