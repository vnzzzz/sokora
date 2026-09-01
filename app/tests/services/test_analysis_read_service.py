"""Analysis page read model tests."""

from datetime import date

from sqlalchemy.orm import Session

from app import models
from app.services import analysis_read_service


def _add_reference_data(db: Session) -> dict[str, object]:
    groups = {
        "first": models.Group(name="Analysis Group First", order=10),
        "later": models.Group(name="Analysis Group Later", order=20),
        "unordered": models.Group(name="Analysis Group Unordered", order=None),
    }
    user_types = {
        "first": models.UserType(name="Analysis Type First", order=10),
        "later": models.UserType(name="Analysis Type Later", order=20),
    }
    locations = {
        "zero": models.Location(
            name="Analysis Office Zero",
            category="Office",
            order=0,
        ),
        "later": models.Location(
            name="Analysis Office Later",
            category="Office",
            order=20,
        ),
        "unordered": models.Location(
            name="Analysis Office Unordered",
            category="Office",
            order=None,
        ),
    }
    db.add_all([*groups.values(), *user_types.values(), *locations.values()])
    db.flush()

    users = {
        "alpha": models.User(
            id="analysis-alpha",
            username="Alpha",
            group_id=groups["later"].id,
            user_type_id=user_types["first"].id,
        ),
        "zeta": models.User(
            id="analysis-zeta",
            username="Zeta",
            group_id=groups["later"].id,
            user_type_id=user_types["later"].id,
        ),
        "beta": models.User(
            id="analysis-beta",
            username="Beta",
            group_id=groups["first"].id,
            user_type_id=user_types["first"].id,
        ),
        "omega": models.User(
            id="analysis-omega",
            username="Omega",
            group_id=groups["unordered"].id,
            user_type_id=user_types["first"].id,
        ),
    }
    db.add_all(users.values())
    db.flush()

    db.add_all(
        [
            models.Attendance(
                user_id="analysis-alpha",
                date=date(2031, 5, 3),
                location_id=locations["zero"].id,
                note="alpha zero",
            ),
            models.Attendance(
                user_id="analysis-alpha",
                date=date(2031, 5, 4),
                location_id=locations["later"].id,
            ),
            models.Attendance(
                user_id="analysis-zeta",
                date=date(2031, 5, 5),
                location_id=locations["zero"].id,
            ),
            models.Attendance(
                user_id="analysis-beta",
                date=date(2031, 5, 6),
                location_id=locations["zero"].id,
            ),
            models.Attendance(
                user_id="analysis-omega",
                date=date(2031, 5, 7),
                location_id=locations["zero"].id,
            ),
        ]
    )
    db.commit()
    return {
        "groups": groups,
        "user_types": user_types,
        "locations": locations,
    }


def test_month_view_model_owns_grouping_sorting_and_location_categories(
    db_with_data: Session,
) -> None:
    db = db_with_data
    _add_reference_data(db)

    view_model = analysis_read_service.get_analysis_page_view_model(
        db,
        month="2031-05",
        today=date(2031, 5, 15),
    )

    assert view_model["is_year_mode"] is False
    assert view_model["analysis_data"]["period"]["label"] == "2031年5月"
    assert view_model["current_month"] == "2031-05"

    assert [section["name"] for section in view_model["group_sections"]] == [
        "Analysis Group First",
        "Analysis Group Later",
        "Analysis Group Unordered",
    ]

    later_group = view_model["group_sections"][1]
    assert [section["name"] for section in later_group["user_types"]] == [
        "Analysis Type First",
        "Analysis Type Later",
    ]
    alpha = later_group["user_types"][0]["users"][0]
    assert alpha["user_name"] == "Alpha"
    assert alpha["total_days"] == 2
    assert [group["location_name"] for group in alpha["date_groups"]] == [
        "Analysis Office Zero",
        "Analysis Office Later",
    ]

    office_category = next(
        category
        for category in view_model["location_categories"]
        if category["name"] == "Office"
    )
    assert [str(location.name) for location in office_category["locations"]] == [
        "Analysis Office Zero",
        "Analysis Office Later",
        "Analysis Office Unordered",
    ]
    assert view_model["location_categories"][-1]["name"] == "未分類"


def test_fiscal_year_view_model_uses_april_to_march_period(
    db_with_data: Session,
) -> None:
    _add_reference_data(db_with_data)

    view_model = analysis_read_service.get_analysis_page_view_model(
        db_with_data,
        mode="year",
        year=2031,
        today=date(2031, 5, 15),
    )

    period = view_model["analysis_data"]["period"]
    assert view_model["is_year_mode"] is True
    assert view_model["current_year"] == 2031
    assert period["label"] == "2031年度"
    assert period["start"] == date(2031, 4, 1)
    assert period["end"] == date(2032, 3, 31)


def test_error_view_model_is_render_safe() -> None:
    view_model = analysis_read_service.get_error_page_view_model(
        month="invalid",
        today=date(2031, 5, 15),
    )

    assert view_model["analysis_data"]["period"]["mode"] == "error"
    assert view_model["current_month"] == "invalid"
    assert view_model["group_sections"] == []
    assert view_model["location_categories"] == []
