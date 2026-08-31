from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.session import create_database_runtime, migrate_database
from app.models.attendance import Attendance
from app.models.group import Group
from app.models.location import Location
from app.models.user import User
from app.models.user_type import UserType


def _migrated_runtime(tmp_path: Path):
    runtime = create_database_runtime(f"sqlite:///{tmp_path / 'integrity.db'}")
    migrate_database(runtime)
    return runtime


def _seed_reference_rows(runtime) -> None:
    with runtime.session_factory() as db:
        db.add_all(
            [
                Group(id=1, name="group"),
                UserType(id=1, name="type"),
                Location(id=1, name="office"),
            ]
        )
        db.commit()
        db.add(User(id="u1", username="User 1", group_id=1, user_type_id=1))
        db.commit()


def test_migration_adds_attendance_user_date_unique_constraint(tmp_path: Path) -> None:
    runtime = _migrated_runtime(tmp_path)
    try:
        constraints = inspect(runtime.engine).get_unique_constraints("attendance")
        assert any(
            constraint["name"] == "uq_attendance_user_date"
            and set(constraint["column_names"]) == {"user_id", "date"}
            for constraint in constraints
        )
    finally:
        runtime.dispose()


def test_migration_rejects_existing_duplicates_without_deleting_data(
    tmp_path: Path,
) -> None:
    runtime = create_database_runtime(f"sqlite:///{tmp_path / 'duplicates.db'}")
    try:
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    "create table attendance ("
                    "id integer primary key, "
                    "user_id varchar not null, "
                    "date date not null, "
                    "location_id integer not null, "
                    "note varchar)"
                )
            )
            connection.execute(
                text(
                    "create table alembic_version ("
                    "version_num varchar(32) not null primary key)"
                )
            )
            connection.execute(
                text(
                    "insert into alembic_version(version_num) "
                    "values ('2f6c8d1e9a4b')"
                )
            )
            connection.execute(
                text(
                    "insert into attendance "
                    "(id, user_id, date, location_id) values "
                    "(1, 'u1', '2030-01-01', 1), "
                    "(2, 'u1', '2030-01-01', 1)"
                )
            )

        with pytest.raises(RuntimeError, match="resolve duplicates"):
            migrate_database(runtime)

        with runtime.session_factory() as db:
            assert db.scalar(text("select count(*) from attendance")) == 2
            assert (
                db.scalar(text("select version_num from alembic_version"))
                == "2f6c8d1e9a4b"
            )
    finally:
        runtime.dispose()


def test_sqlite_runtime_enforces_foreign_keys(tmp_path: Path) -> None:
    runtime = _migrated_runtime(tmp_path)
    try:
        with runtime.session_factory() as db:
            assert db.scalar(text("PRAGMA foreign_keys")) == 1
            db.add(
                User(
                    id="orphan",
                    username="Orphan",
                    group_id=999,
                    user_type_id=999,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
    finally:
        runtime.dispose()


def test_database_rejects_duplicate_attendance_user_date(tmp_path: Path) -> None:
    runtime = _migrated_runtime(tmp_path)
    try:
        _seed_reference_rows(runtime)
        with runtime.session_factory() as db:
            db.add(
                Attendance(
                    user_id="u1",
                    date=date(2030, 1, 1),
                    location_id=1,
                )
            )
            db.commit()

        # Simulate a second writer that did not observe the first row. The DB,
        # not an application-side pre-check, is the final concurrency guard.
        with runtime.session_factory() as db:
            db.add(
                Attendance(
                    user_id="u1",
                    date=date(2030, 1, 1),
                    location_id=1,
                )
            )
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()

            assert (
                db.query(Attendance)
                .filter(
                    Attendance.user_id == "u1",
                    Attendance.date == date(2030, 1, 1),
                )
                .count()
                == 1
            )
    finally:
        runtime.dispose()
