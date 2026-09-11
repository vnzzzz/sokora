"""Analysis coverage presentation tests."""

from datetime import date
from types import SimpleNamespace
from typing import Any, Dict, List

from app.services import analysis_coverage_service
from app.services.analysis_read_service import GroupSection
from app.utils.ui_utils import get_location_tone


def _analysis_data(period_start: date = date(2031, 5, 1)) -> Dict[str, Any]:
    return {
        "period": {
            "start": period_start,
        },
        "locations": [
            SimpleNamespace(id=1, name="Office"),
            SimpleNamespace(id=2, name="Remote"),
        ],
        "users": {
            "u1": {
                "group_name": "Design",
                "user_type_name": "Employee",
            },
            "u2": {
                "group_name": "Design",
                "user_type_name": "Contractor",
            },
            "u3": {
                "group_name": "Sales",
                "user_type_name": "Employee",
            },
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
            "user_types": [
                {"name": "Employee", "users": []},
            ],
        },
    ]


def _cells_by_key(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {cell["key"]: cell for cell in row["cells"]}


def test_month_coverage_counts_unique_people_and_type_breakdown() -> None:
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

    group_rows = {row["label"]: row for row in view_model["group_coverage_rows"]}
    design_cells = _cells_by_key(group_rows["Design"])
    sales_cells = _cells_by_key(group_rows["Sales"])

    assert group_rows["Design"]["member_count"] == 2
    assert design_cells["2031-05-03"]["total"] == 2
    assert design_cells["2031-05-04"]["total"] == 1
    assert sales_cells["2031-05-03"]["total"] == 1

    breakdown = {
        item["name"]: item["count"]
        for item in design_cells["2031-05-03"]["type_counts"]
    }
    assert breakdown == {"Office": 2, "Remote": 1}

    user_type_rows = {
        row["label"]: row for row in view_model["user_type_coverage_rows"]
    }
    employee_cells = _cells_by_key(user_type_rows["Employee"])
    contractor_cells = _cells_by_key(user_type_rows["Contractor"])
    assert employee_cells["2031-05-03"]["total"] == 2
    assert contractor_cells["2031-05-03"]["total"] == 1


def test_selected_work_type_exposes_zero_coverage_days() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[2],
        is_year_mode=False,
    )

    group_rows = {row["label"]: row for row in view_model["group_coverage_rows"]}
    design_cells = _cells_by_key(group_rows["Design"])
    sales_cells = _cells_by_key(group_rows["Sales"])

    assert design_cells["2031-05-03"]["total"] == 1
    assert design_cells["2031-05-04"]["total"] == 0
    assert sales_cells["2031-05-03"]["total"] == 1
    assert view_model["coverage_locations"][0]["name"] == "Remote"


def test_year_coverage_counts_unique_people_per_month() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(date(2031, 4, 1)),
        group_sections=_group_sections(),
        selected_location_ids=[1, 2],
        is_year_mode=True,
    )

    group_rows = {row["label"]: row for row in view_model["group_coverage_rows"]}
    design_cells = _cells_by_key(group_rows["Design"])

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
    assert design_cells["2031-05"]["total"] == 2


def test_empty_selection_keeps_rows_but_sets_all_counts_to_zero() -> None:
    view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=_analysis_data(),
        group_sections=_group_sections(),
        selected_location_ids=[],
        is_year_mode=False,
    )

    assert view_model["coverage_locations"] == []
    assert all(
        cell["total"] == 0
        for row in view_model["group_coverage_rows"]
        for cell in row["cells"]
    )
