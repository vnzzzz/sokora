"""Calendar read model service tests."""

from datetime import date

from sqlalchemy import event
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.schemas.user_type import UserTypeCreate
from app.services import calendar_read_service


def _base_ids(db: Session) -> tuple[int, int, int]:
    group = db.query(models.Group).first()
    user_type = db.query(models.UserType).first()
    location = db.query(models.Location).first()
    assert group is not None and group.id is not None
    assert user_type is not None and user_type.id is not None
    assert location is not None and location.id is not None
    return int(group.id), int(user_type.id), int(location.id)


def _create_user(
    db: Session,
    *,
    user_id: str,
    username: str,
    group_id: int,
    user_type_id: int,
) -> None:
    crud.user.create(
        db,
        obj_in=schemas.UserCreate(
            id=user_id,
            username=username,
            group_id=group_id,
            user_type_id=user_type_id,
        ),
    )


def _calendar_day(calendar_data: dict, day: int) -> dict:
    return next(
        day_data
        for week in calendar_data["weeks"]
        for day_data in week
        if day_data["day"] == day
    )


def test_month_view_model_reads_fresh_database_state(db_with_data: Session) -> None:
    db = db_with_data
    group_id, user_type_id, location_id = _base_ids(db)
    location = crud.location.get(db, id=location_id)
    assert location is not None
    first_user_id = "calendar-fresh-a"
    second_user_id = "calendar-fresh-b"
    target_date = date(2031, 5, 1)

    _create_user(
        db,
        user_id=first_user_id,
        username="Calendar Fresh A",
        group_id=group_id,
        user_type_id=user_type_id,
    )
    _create_user(
        db,
        user_id=second_user_id,
        username="Calendar Fresh B",
        group_id=group_id,
        user_type_id=user_type_id,
    )
    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=first_user_id,
            date=target_date,
            location_id=location_id,
        ),
    )
    db.commit()

    first_view = calendar_read_service.get_month_view_model(db, month="2031-05")
    assert _calendar_day(first_view["calendar"], 1)[str(location.name)] == 1

    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=second_user_id,
            date=target_date,
            location_id=location_id,
        ),
    )
    db.commit()

    second_view = calendar_read_service.get_month_view_model(db, month="2031-05")
    assert _calendar_day(second_view["calendar"], 1)[str(location.name)] == 2


def test_day_detail_uses_one_select_and_orders_view_model(
    db_with_data: Session,
) -> None:
    db = db_with_data
    _, _, location_id = _base_ids(db)
    first_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Calendar Group Later", order=20),
    )
    second_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Calendar Group First", order=10),
    )
    unordered_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Calendar Group Unordered", order=None),
    )
    later_type = crud.user_type.create(
        db,
        obj_in=UserTypeCreate(name="Calendar Type Later", order=20),
    )
    first_type = crud.user_type.create(
        db,
        obj_in=UserTypeCreate(name="Calendar Type First", order=10),
    )
    assert first_group.id is not None and second_group.id is not None
    assert unordered_group.id is not None
    assert later_type.id is not None and first_type.id is not None

    _create_user(
        db,
        user_id="calendar-user-z",
        username="Zeta",
        group_id=int(first_group.id),
        user_type_id=int(later_type.id),
    )
    _create_user(
        db,
        user_id="calendar-user-a",
        username="Alpha",
        group_id=int(first_group.id),
        user_type_id=int(first_type.id),
    )
    _create_user(
        db,
        user_id="calendar-user-b",
        username="Beta",
        group_id=int(second_group.id),
        user_type_id=int(first_type.id),
    )
    _create_user(
        db,
        user_id="calendar-user-c",
        username="Gamma",
        group_id=int(unordered_group.id),
        user_type_id=int(first_type.id),
    )
    target_date = date(2031, 6, 2)
    for user_id in (
        "calendar-user-z",
        "calendar-user-a",
        "calendar-user-b",
        "calendar-user-c",
    ):
        crud.attendance.create(
            db,
            obj_in=schemas.AttendanceCreate(
                user_id=user_id,
                date=target_date,
                location_id=location_id,
            ),
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
        view_model = calendar_read_service.get_day_detail_view_model(
            db,
            day=target_date.isoformat(),
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    assert select_count == 1
    assert view_model["has_data"] is True
    assert list(view_model["organized_by_group"]) == [
        "Calendar Group First",
        "Calendar Group Later",
        "Calendar Group Unordered",
    ]
    later_group = view_model["organized_by_group"]["Calendar Group Later"]
    assert later_group["user_types"] == [
        "Calendar Type First",
        "Calendar Type Later",
    ]
    assert later_group["user_types_data"]["Calendar Type First"][0]["user_name"] == (
        "Alpha"
    )


def test_day_detail_null_group_order_is_after_large_explicit_order(
    db_with_data: Session,
) -> None:
    db = db_with_data
    _, user_type_id, location_id = _base_ids(db)
    explicit_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Calendar Group 10000", order=10000),
    )
    unordered_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Calendar Group Null", order=None),
    )
    assert explicit_group.id is not None and unordered_group.id is not None

    _create_user(
        db,
        user_id="calendar-user-explicit",
        username="Explicit",
        group_id=int(explicit_group.id),
        user_type_id=user_type_id,
    )
    _create_user(
        db,
        user_id="calendar-user-null",
        username="Unordered",
        group_id=int(unordered_group.id),
        user_type_id=user_type_id,
    )
    target_date = date(2031, 7, 3)
    for user_id in ("calendar-user-explicit", "calendar-user-null"):
        crud.attendance.create(
            db,
            obj_in=schemas.AttendanceCreate(
                user_id=user_id,
                date=target_date,
                location_id=location_id,
            ),
        )
    db.commit()

    view_model = calendar_read_service.get_day_detail_view_model(
        db,
        day=target_date.isoformat(),
    )

    assert list(view_model["organized_by_group"]) == [
        "Calendar Group 10000",
        "Calendar Group Null",
    ]


def test_invalid_day_returns_empty_view_model(db_with_data: Session) -> None:
    view_model = calendar_read_service.get_day_detail_view_model(
        db_with_data,
        day="not-a-date",
    )

    assert view_model == {
        "date_str": "not-a-date",
        "date_jp": "",
        "organized_by_group": {},
        "has_data": False,
    }
