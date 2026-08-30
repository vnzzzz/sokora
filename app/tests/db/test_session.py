from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register model metadata for schema tests
from app.core.settings import AppSettings
from app.db.session import (
    Base,
    SessionLocal,
    clear_database_runtime_cache,
    create_database_runtime,
    get_db,
    initialize_database,
    migrate_database,
    sqlite_database_path,
)


def test_create_database_runtime_uses_supplied_database_url(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    database_url = f"sqlite:///{database_path}"

    runtime = create_database_runtime(database_url)
    try:
        assert str(runtime.engine.url) == database_url
        with runtime.session_factory() as db:
            assert db.scalar(text("select 1")) == 1
    finally:
        runtime.dispose()


def test_create_database_runtime_shares_sqlite_uri_memory_database() -> None:
    database_url = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

    runtime = create_database_runtime(database_url)
    try:
        assert isinstance(runtime.engine.pool, StaticPool)
    finally:
        runtime.dispose()


def test_sqlite_database_path_resolves_file_urls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    uri_path = tmp_path / "uri database.db"
    encoded_uri_path = quote(str(uri_path), safe="/")

    assert sqlite_database_path("sqlite:///data/sokora.db") == (
        tmp_path / "data" / "sokora.db"
    )
    assert (
        sqlite_database_path(f"sqlite:///file:{encoded_uri_path}?uri=true") == uri_path
    )
    assert sqlite_database_path("sqlite:///:memory:") is None
    assert sqlite_database_path("sqlite:///file::memory:?cache=shared&uri=true") is None
    assert (
        sqlite_database_path("sqlite:///file:memdb2?mode=memory&cache=shared&uri=true")
        is None
    )
    assert sqlite_database_path("postgresql://db.example/sokora") is None


def test_migrate_database_creates_parent_and_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "sokora.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    try:
        migrate_database(runtime)

        assert database_path.exists()
        table_names = inspect(runtime.engine).get_table_names()
        assert "alembic_version" in table_names
        assert "users" in table_names
        assert "attendance" in table_names
    finally:
        runtime.dispose()


def test_migrate_database_uses_runtime_connection_for_sqlite_memory() -> None:
    runtime = create_database_runtime("sqlite:///:memory:")
    try:
        migrate_database(runtime)

        table_names = inspect(runtime.engine).get_table_names()
        assert "users" in table_names
        assert "attendance" in table_names
        with runtime.session_factory() as db:
            assert db.scalar(text("select version_num from alembic_version"))
    finally:
        runtime.dispose()


def test_migrate_database_adopts_unversioned_current_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "unversioned.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    try:
        # Reproduce a database created by the pre-#54 create_all lifecycle.
        Base.metadata.create_all(bind=runtime.engine)
        assert "alembic_version" not in inspect(runtime.engine).get_table_names()
        custom_holiday_columns = {
            column["name"]: column
            for column in inspect(runtime.engine).get_columns("custom_holidays")
        }
        assert custom_holiday_columns["created_at"]["default"] is None
        assert custom_holiday_columns["updated_at"]["default"] is None

        # Existing application data must survive the schema adoption/normalization.
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    "insert into custom_holidays "
                    "(date, name, created_at, updated_at) "
                    "values ('2030-01-01', 'legacy holiday', "
                    "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
                )
            )

        migrate_database(runtime)

        with runtime.session_factory() as db:
            first_revision = db.scalar(text("select version_num from alembic_version"))
            assert (
                db.scalar(
                    text("select name from custom_holidays where date = '2030-01-01'")
                )
                == "legacy holiday"
            )
        assert first_revision

        # Adopted create_all databases converge to the same DB-side defaults as
        # databases that reached the legacy Alembic head through migrations.
        custom_holiday_columns = {
            column["name"]: column
            for column in inspect(runtime.engine).get_columns("custom_holidays")
        }
        assert custom_holiday_columns["created_at"]["default"] is not None
        assert custom_holiday_columns["updated_at"]["default"] is not None

        # Once adopted, subsequent migrations are idempotent at head.
        migrate_database(runtime)
        with runtime.session_factory() as db:
            assert (
                db.scalar(text("select version_num from alembic_version"))
                == first_revision
            )
    finally:
        runtime.dispose()


def test_migrate_database_adopts_pre_custom_holidays_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "pre-custom-holidays.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    try:
        # Reproduce the c678232-era create_all schema: the first four legacy
        # changes were already represented in the models, but custom_holidays
        # did not exist yet and there was no Alembic version marker.
        Base.metadata.create_all(bind=runtime.engine)
        with runtime.engine.begin() as connection:
            connection.execute(text("drop table custom_holidays"))
            connection.execute(
                text(
                    'insert into groups (id, name, "order") '
                    "values (101, 'legacy group', 7)"
                )
            )

        table_names = inspect(runtime.engine).get_table_names()
        assert "custom_holidays" not in table_names
        assert "alembic_version" not in table_names

        migrate_database(runtime)

        table_names = inspect(runtime.engine).get_table_names()
        assert "custom_holidays" in table_names
        assert "alembic_version" in table_names
        with runtime.session_factory() as db:
            assert db.scalar(text("select version_num from alembic_version"))
            assert (
                db.scalar(text("select name from groups where id = 101"))
                == "legacy group"
            )
    finally:
        runtime.dispose()


def test_initialize_database_seeds_only_when_sqlite_file_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "sokora.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    seed_calls: list[str] = []

    def fake_seed(*_args, **_kwargs) -> dict[str, int]:
        seed_calls.append("seeded")
        return {"attendances": 0}

    monkeypatch.setattr("app.db.session.seed_database", fake_seed)
    try:
        assert initialize_database(runtime) is True
        assert seed_calls == ["seeded"]

        assert initialize_database(runtime) is True
        assert seed_calls == ["seeded"]
    finally:
        runtime.dispose()


def test_initialize_database_does_not_reseed_existing_sqlite_uri(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "existing uri.db"
    encoded_database_path = quote(str(database_path), safe="/")
    database_url = f"sqlite:///file:{encoded_database_path}?uri=true"
    runtime = create_database_runtime(database_url)
    seed_calls: list[str] = []

    def fake_seed(*_args, **_kwargs) -> dict[str, int]:
        seed_calls.append("seeded")
        return {"attendances": 0}

    try:
        migrate_database(runtime)
        assert database_path.exists()

        monkeypatch.setattr("app.db.session.seed_database", fake_seed)
        assert initialize_database(runtime) is True
        assert seed_calls == []
    finally:
        runtime.dispose()


def test_session_local_uses_database_url_from_environment(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "env.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    clear_database_runtime_cache()

    session = SessionLocal()
    try:
        assert isinstance(session, Session)
        assert str(session.get_bind().url) == f"sqlite:///{database_path}"
    finally:
        session.close()
        clear_database_runtime_cache()


def test_get_db_uses_application_scoped_runtime(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"
    settings = AppSettings(database_url=f"sqlite:///{database_path}")
    app = FastAPI()
    app.state.settings_provider = lambda: settings

    from starlette.requests import Request

    scope = {
        "type": "http",
        "app": app,
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "scheme": "http",
        "root_path": "",
        "http_version": "1.1",
    }
    request = Request(scope)

    generator = get_db(request)
    session = next(generator)
    try:
        assert str(session.get_bind().url) == settings.database_url
    finally:
        generator.close()
        app.state.database_runtime.dispose()
