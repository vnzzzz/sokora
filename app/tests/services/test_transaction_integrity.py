from datetime import date

import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services import attendance_service, user_service
from app.services.errors import DataIntegrityError


def _reference_rows(
    db: Session,
) -> tuple[models.Group, models.UserType, models.Location]:
    group = db.query(models.Group).filter(models.Group.name == "Test Group").one()
    user_type = (
        db.query(models.UserType).filter(models.UserType.name == "Test Type").one()
    )
    location = (
        db.query(models.Location).filter(models.Location.name == "Test Location").one()
    )
    return group, user_type, location


def _create_user(db: Session, *, user_id: str = "tx-user") -> models.User:
    group, user_type, _location = _reference_rows(db)
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


def test_duplicate_write_is_translated_after_stale_precheck(
    db_with_data: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = db_with_data
    _group, _user_type, location = _reference_rows(db)
    user = _create_user(db)
    target_date = date(2030, 1, 1)

    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=str(user.id),
            date=target_date,
            location_id=int(location.id),
        ),
    )
    db.commit()

    # Model a concurrent race: the service-side pre-check saw no row, while a
    # competing writer committed the same key before this writer flushed.
    monkeypatch.setattr(
        crud.attendance,
        "get_by_user_and_date",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(DataIntegrityError):
        attendance_service.create_attendance(
            db,
            user_id=str(user.id),
            attendance_date=target_date,
            location_id=int(location.id),
        )

    assert (
        db.query(models.Attendance)
        .filter(
            models.Attendance.user_id == user.id,
            models.Attendance.date == target_date,
        )
        .count()
        == 1
    )


def test_user_delete_rolls_back_attendance_delete_when_user_delete_fails(
    db_with_data: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = db_with_data
    _group, _user_type, location = _reference_rows(db)
    user = _create_user(db, user_id="atomic-user")
    attendance = crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=str(user.id),
            date=date(2030, 2, 1),
            location_id=int(location.id),
        ),
    )
    db.commit()

    def fail_user_delete(*_args, **_kwargs):
        raise RuntimeError("forced user delete failure")

    monkeypatch.setattr(crud.user, "remove", fail_user_delete)

    with pytest.raises(RuntimeError, match="forced user delete failure"):
        user_service.delete_user(db, user_id=str(user.id))

    assert db.get(models.User, user.id) is not None
    assert db.get(models.Attendance, attendance.id) is not None
