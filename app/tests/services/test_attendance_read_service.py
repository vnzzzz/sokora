"""Attendance weekly/monthly read-model service contracts."""

from sqlalchemy.orm import Session

from app import crud, schemas
from app.services import attendance_read_service


def test_monthly_directory_orders_nullable_group_and_user_type_last(
    db: Session,
) -> None:
    explicit_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Explicit Group", order=10_000),
    )
    null_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Null Group", order=None),
    )
    explicit_type = crud.user_type.create(
        db,
        obj_in=schemas.UserTypeCreate(name="Explicit Type", order=10_000),
    )
    null_type = crud.user_type.create(
        db,
        obj_in=schemas.UserTypeCreate(name="Null Type", order=None),
    )
    assert explicit_group.id is not None
    assert null_group.id is not None
    assert explicit_type.id is not None
    assert null_type.id is not None

    for user_id, username, group_id, user_type_id in (
        (
            "explicit-user",
            "Explicit User",
            int(explicit_group.id),
            int(explicit_type.id),
        ),
        (
            "null-type-user",
            "Null Type User",
            int(explicit_group.id),
            int(null_type.id),
        ),
        (
            "null-group-user",
            "Null Group User",
            int(null_group.id),
            int(explicit_type.id),
        ),
    ):
        crud.user.create(
            db,
            obj_in=schemas.UserCreate(
                id=user_id,
                username=username,
                group_id=group_id,
                user_type_id=user_type_id,
            ),
        )
    db.commit()
    db.expire_all()

    view_model = attendance_read_service.get_monthly_register_page_view_model(
        db,
        month="2031-05",
    )

    assert view_model["group_names"] == ["Explicit Group", "Null Group"]
    explicit_sections = view_model["grouped_users"]["Explicit Group"]
    assert [section[1] for section in explicit_sections] == [
        "Explicit Type",
        "Null Type",
    ]


def test_weekly_view_model_includes_all_locations_without_default_pagination(
    db: Session,
) -> None:
    for index in range(101):
        crud.location.create(
            db,
            obj_in=schemas.LocationCreate(
                name=f"Read Location {index:03d}",
                category="office",
                order=index,
            ),
        )
    db.commit()

    view_model = attendance_read_service.get_weekly_page_view_model(
        db,
        week="2031-05-12",
    )

    assert len(view_model["location_objects"]) == 101
