"""Analysis day-detail read-path regression tests."""

from datetime import date

from sqlalchemy import event
from sqlalchemy.orm import Session

from app import models
from app.services import analysis_day_detail_service


def test_location_filter_preserves_single_select_read_path(db_with_data: Session) -> None:
    db = db_with_data
    group = db.query(models.Group).first()
    user_type = db.query(models.UserType).first()
    selected_location = db.query(models.Location).first()
    assert group is not None and group.id is not None
    assert user_type is not None and user_type.id is not None
    assert selected_location is not None and selected_location.id is not None

    other_location = models.Location(
        name="Analysis Query Other Location",
        category="勤務",
        order=999,
    )
    db.add(other_location)
    db.flush()
    assert other_location.id is not None

    selected_location_id = int(selected_location.id)
    other_location_id = int(other_location.id)
    group_id = int(group.id)
    user_type_id = int(user_type.id)
    target_date = date(2040, 1, 2)

    db.add_all(
        [
            models.User(
                id="analysis-query-selected",
                username="Analysis Query Selected",
                group_id=group_id,
                user_type_id=user_type_id,
            ),
            models.User(
                id="analysis-query-other",
                username="Analysis Query Other",
                group_id=group_id,
                user_type_id=user_type_id,
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            models.Attendance(
                user_id="analysis-query-selected",
                date=target_date,
                location_id=selected_location_id,
            ),
            models.Attendance(
                user_id="analysis-query-other",
                date=target_date,
                location_id=other_location_id,
            ),
        ]
    )
    db.commit()

    select_count = 0
    engine = db.get_bind()

    def count_selects(
        _conn,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        view_model = analysis_day_detail_service.get_filtered_day_detail_view_model(
            db,
            day=target_date,
            selected_location_ids=[selected_location_id],
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    users = [
        user
        for group_data in view_model["organized_by_group"].values()
        for user_type_name in group_data["user_types"]
        for user in group_data["user_types_data"][user_type_name]
    ]

    assert select_count == 1
    assert [user["user_id"] for user in users] == ["analysis-query-selected"]
    assert users[0]["location_id"] == selected_location_id
