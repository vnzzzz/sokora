from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.settings import AppSettings
from app.db.session import create_database_runtime, initialize_database
from app.main import create_application


def _prepare_duplicate_attendance_database(database_path: Path) -> str:
    database_url = f"sqlite:///{database_path}"
    runtime = create_database_runtime(database_url)
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
    finally:
        runtime.dispose()
    return database_url


def test_initialize_database_propagates_duplicate_migration_failure(
    tmp_path: Path,
) -> None:
    database_url = _prepare_duplicate_attendance_database(tmp_path / "duplicates.db")
    runtime = create_database_runtime(database_url)
    try:
        with pytest.raises(RuntimeError, match="resolve duplicates"):
            initialize_database(runtime)

        with runtime.session_factory() as db:
            assert db.scalar(text("select count(*) from attendance")) == 2
            assert (
                db.scalar(text("select version_num from alembic_version"))
                == "2f6c8d1e9a4b"
            )
    finally:
        runtime.dispose()


def test_application_startup_aborts_when_migration_fails(tmp_path: Path) -> None:
    database_url = _prepare_duplicate_attendance_database(
        tmp_path / "startup-duplicates.db"
    )
    app = create_application(AppSettings(database_url=database_url))

    with pytest.raises(RuntimeError, match="resolve duplicates"):
        with TestClient(app):
            pass

    assert app.state.database_runtime is None
