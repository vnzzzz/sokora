"""Master-management list read-model contracts."""

from sqlalchemy import event
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import master_read_service


def test_user_master_view_model_groups_orders_and_eager_loads_relationships(
    db: Session,
) -> None:
    first_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="first-group", order=10_000),
    )
    unordered_group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="unordered-group", order=None),
    )
    first_type = crud.user_type.create(
        db,
        obj_in=schemas.UserTypeCreate(name="first-type", order=20),
    )
    second_type = crud.user_type.create(
        db,
        obj_in=schemas.UserTypeCreate(name="second-type", order=10),
    )
    db.commit()
    assert first_group.id is not None
    assert unordered_group.id is not None
    assert first_type.id is not None
    assert second_type.id is not None

    crud.user.create(
        db,
        obj_in=schemas.UserCreate(
            id="user-b",
            username="Beta",
            group_id=int(first_group.id),
            user_type_id=int(second_type.id),
        ),
    )
    crud.user.create(
        db,
        obj_in=schemas.UserCreate(
            id="user-a",
            username="Alpha",
            group_id=int(first_group.id),
            user_type_id=int(first_type.id),
        ),
    )
    crud.user.create(
        db,
        obj_in=schemas.UserCreate(
            id="user-c",
            username="Gamma",
            group_id=int(unordered_group.id),
            user_type_id=int(first_type.id),
        ),
    )
    db.commit()
    db.expire_all()

    select_count = 0

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

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        view = master_read_service.get_user_master_page_view_model(db)
        relationship_names = [
            (str(user.group.name), str(user.user_type.name)) for user in view.users
        ]
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    assert select_count == 3
    assert len(relationship_names) == 3
    assert view.group_names == ["first-group", "unordered-group"]
    assert [str(user.id) for user in view.grouped_users["first-group"]] == [
        "user-a",
        "user-b",
    ]


def test_location_master_view_model_groups_in_query_order(db: Session) -> None:
    crud.location.create(
        db,
        obj_in=schemas.LocationCreate(name="office-b", category="office", order=20),
    )
    crud.location.create(
        db,
        obj_in=schemas.LocationCreate(name="remote", category=None, order=10),
    )
    crud.location.create(
        db,
        obj_in=schemas.LocationCreate(name="office-a", category="office", order=10),
    )
    db.commit()

    view = master_read_service.get_location_master_page_view_model(db)

    assert view.category_names == ["office", "未分類"]
    assert [str(location.name) for location in view.grouped_locations["office"]] == [
        "office-a",
        "office-b",
    ]
    assert [str(location.name) for location in view.grouped_locations["未分類"]] == [
        "remote"
    ]
