from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register model metadata for schema tests
from app.core.settings import AppSettings
from app.db.session import (
    SessionLocal,
    clear_database_runtime_cache,
    create_database_runtime,
    get_db,
    init_db,
    initialize_database,
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
        sqlite_database_path(f"sqlite:///file:{encoded_uri_path}?uri=true")
        == uri_path
    )
    assert sqlite_database_path("sqlite:///:memory:") is None
    assert sqlite_database_path("sqlite:///file::memory:?cache=shared&uri=true") is None
    assert (
        sqlite_database_path(
            "sqlite:///file:memdb2?mode=memory&cache=shared&uri=true"
        )
        is None
    )
    assert sqlite_database_path("postgresql://db.example/sokora") is None


def test_init_db_creates_parent_and_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "sokora.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    try:
        init_db(runtime)

        assert database_path.exists()
        assert "users" in inspect(runtime.engine).get_table_names()
        assert "attendance" in inspect(runtime.engine).get_table_names()
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
        init_db(runtime)
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
