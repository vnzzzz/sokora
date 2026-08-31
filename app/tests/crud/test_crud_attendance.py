from datetime import date

from sqlalchemy.orm import Session

from app import crud, models, schemas


def _references(db: Session) -> tuple[models.Group, models.UserType, models.Location]:
    group = db.query(models.Group).first()
    user_type = db.query(models.UserType).first()
    location = db.query(models.Location).first()
    assert group is not None
    assert user_type is not None
    assert location is not None
    return group, user_type, location


def _user(db: Session, *, user_id: str) -> models.User:
    group, user_type, _ = _references(db)
    created = crud.user.create(
        db,
        obj_in=schemas.UserCreate(
            id=user_id,
            username=f"User {user_id}",
            group_id=int(group.id),
            user_type_id=int(user_type.id),
        ),
    )
    db.commit()
    return created


def test_get_by_user_and_date_and_user_projection(db_with_data: Session) -> None:
    db = db_with_data
    _, _, location = _references(db)
    user = _user(db, user_id="crud-attendance-user")
    target_date = date(2031, 1, 10)
    created = crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=str(user.id),
            date=target_date,
            location_id=int(location.id),
            note="projection note",
        ),
    )
    db.commit()

    found = crud.attendance.get_by_user_and_date(
        db, user_id=str(user.id), date=target_date
    )
    assert found is not None
    assert found.id == created.id

    projection = crud.attendance.get_user_data(db, user_id=str(user.id))
    assert projection == [
        {
            "id": created.id,
            "date": target_date.isoformat(),
            "location_id": int(location.id),
            "location_name": location.name,
            "note": "projection note",
        }
    ]


def test_day_projection_is_fresh_without_process_cache(db_with_data: Session) -> None:
    db = db_with_data
    _, _, location = _references(db)
    first_user = _user(db, user_id="fresh-user-a")
    second_user = _user(db, user_id="fresh-user-b")
    target_date = date(2031, 2, 3)

    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=str(first_user.id),
            date=target_date,
            location_id=int(location.id),
        ),
    )
    db.commit()
    first_read = crud.attendance.get_day_data(db, day=target_date.isoformat())
    assert sum(len(rows) for rows in first_read.values()) == 1

    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=str(second_user.id),
            date=target_date,
            location_id=int(location.id),
        ),
    )
    db.commit()
    second_read = crud.attendance.get_day_data(db, day=target_date.isoformat())
    assert sum(len(rows) for rows in second_read.values()) == 2


def test_period_and_export_queries_return_database_rows(db_with_data: Session) -> None:
    db = db_with_data
    _, _, location = _references(db)
    user = _user(db, user_id="query-user")
    target_date = date(2031, 3, 4)
    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=str(user.id),
            date=target_date,
            location_id=int(location.id),
        ),
    )
    db.commit()

    period_rows = crud.attendance.list_for_period(
        db, start_date=target_date, end_date=target_date
    )
    assert [str(row.user_id) for row in period_rows] == [str(user.id)]

    export_rows = crud.attendance.list_export_rows(
        db, start_date=target_date, end_date=target_date
    )
    assert len(export_rows) == 1
    assert str(export_rows[0].user_id) == str(user.id)
    assert export_rows[0].location_name == location.name
