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


def _legacy_runtime_with_inbound_foreign_key(tmp_path: Path):
    runtime = create_database_runtime(f"sqlite:///{tmp_path / 'legacy-with-fks.db'}")
    with runtime.engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE groups (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE user_types (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE locations (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE users (
                id VARCHAR PRIMARY KEY,
                username VARCHAR NOT NULL,
                group_id INTEGER NOT NULL REFERENCES groups(id),
                user_type_id INTEGER NOT NULL REFERENCES user_types(id)
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                date DATE NOT NULL,
                location_id INTEGER NOT NULL REFERENCES locations(id),
                note VARCHAR,
                CONSTRAINT uq_attendance_user_date UNIQUE(user_id, date)
            )
            """
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            )
            """
        )
        connection.exec_driver_sql("INSERT INTO groups(id, name) VALUES (1, 'Group')")
        connection.exec_driver_sql(
            "INSERT INTO user_types(id, name) VALUES (1, 'Type')"
        )
        connection.exec_driver_sql(
            "INSERT INTO locations(id, name) VALUES (1, 'Office')"
        )
        connection.exec_driver_sql(
            """
            INSERT INTO users(id, username, group_id, user_type_id)
            VALUES ('u1', 'Legacy User', 1, 1)
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO attendance(id, user_id, date, location_id)
            VALUES (1, 'u1', '2030-01-01', 1)
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO alembic_version(version_num)
            VALUES ('7c4a1b2d3e5f')
            """
        )
    return runtime


def test_sqlite_migration_handles_existing_rows_with_inbound_foreign_keys(
    tmp_path: Path,
) -> None:
    runtime = _legacy_runtime_with_inbound_foreign_key(tmp_path)
    try:
        migrate_database(runtime)

        with runtime.engine.connect() as connection:
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
            assert connection.scalar(text("SELECT COUNT(*) FROM users")) == 1
            assert connection.scalar(text("SELECT COUNT(*) FROM attendance")) == 1

        constraints = inspect(runtime.engine).get_unique_constraints("users")
        assert any(
            constraint["name"] == "uq_users_username"
            and set(constraint["column_names"]) == {"username"}
            for constraint in constraints
        )
    finally:
        runtime.dispose()


def test_sqlite_migration_rolls_back_when_foreign_key_check_fails(
    tmp_path: Path,
) -> None:
    runtime = _legacy_runtime_with_inbound_foreign_key(tmp_path)
    try:
        with runtime.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            connection.exec_driver_sql(
                "UPDATE attendance SET user_id='missing-user' WHERE id=1"
            )
            connection.commit()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()

        with pytest.raises(RuntimeError, match="foreign key check failed"):
            migrate_database(runtime)

        with runtime.engine.connect() as connection:
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "7c4a1b2d3e5f"
            )
            assert (
                connection.scalar(text("SELECT user_id FROM attendance WHERE id=1"))
                == "missing-user"
            )
            assert (
                connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM sqlite_master "
                        "WHERE name = '_alembic_tmp_users'"
                    )
                )
                == 0
            )

        with runtime.engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE attendance SET user_id='u1' WHERE id=1"
            )

        migrate_database(runtime)

        with runtime.engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
            assert (
                connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM sqlite_master "
                        "WHERE name = '_alembic_tmp_users'"
                    )
                )
                == 0
            )
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                != "7c4a1b2d3e5f"
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


def test_migration_adds_user_username_unique_constraint(tmp_path: Path) -> None:
    runtime = _migrated_runtime(tmp_path)
    try:
        constraints = inspect(runtime.engine).get_unique_constraints("users")
        assert any(
            constraint["name"] == "uq_users_username"
            and set(constraint["column_names"]) == {"username"}
            for constraint in constraints
        )
    finally:
        runtime.dispose()


def test_migration_rejects_existing_duplicate_usernames_without_deleting_data(
    tmp_path: Path,
) -> None:
    runtime = create_database_runtime(f"sqlite:///{tmp_path / 'user-duplicates.db'}")
    try:
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    "create table users ("
                    "id varchar primary key, "
                    "username varchar not null, "
                    "group_id integer not null, "
                    "user_type_id integer not null)"
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
                    "values ('7c4a1b2d3e5f')"
                )
            )
            connection.execute(
                text(
                    "insert into users "
                    "(id, username, group_id, user_type_id) values "
                    "('u1', 'Duplicate Name', 1, 1), "
                    "('u2', 'Duplicate Name', 1, 1)"
                )
            )

        with pytest.raises(RuntimeError, match="resolve duplicates"):
            migrate_database(runtime)

        with runtime.session_factory() as db:
            assert db.scalar(text("PRAGMA foreign_keys")) == 1
            assert db.scalar(text("select count(*) from users")) == 2
            assert (
                db.scalar(text("select version_num from alembic_version"))
                == "7c4a1b2d3e5f"
            )
    finally:
        runtime.dispose()


def test_database_rejects_duplicate_usernames(tmp_path: Path) -> None:
    runtime = _migrated_runtime(tmp_path)
    try:
        _seed_reference_rows(runtime)

        with runtime.session_factory() as db:
            db.add(User(id="u2", username="User 1", group_id=1, user_type_id=1))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()

            assert db.query(User).filter(User.username == "User 1").count() == 1
    finally:
        runtime.dispose()
