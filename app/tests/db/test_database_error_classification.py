import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.session import create_database_runtime, is_database_unavailable_error


def _operational_error_with_sqlstate(sqlstate: str) -> OperationalError:
    original = RuntimeError(f"postgresql error {sqlstate}")
    original.sqlstate = sqlstate  # type: ignore[attr-defined]
    return OperationalError(None, {}, original)


def test_integrity_error_without_statement_is_not_database_unavailable() -> None:
    error = IntegrityError(
        None,
        {},
        RuntimeError("deferred foreign key violation"),
    )

    assert is_database_unavailable_error(error) is False


def test_postgresql_connection_sqlstate_is_database_unavailable() -> None:
    error = _operational_error_with_sqlstate("08006")

    assert is_database_unavailable_error(error) is True


def test_postgresql_cannot_connect_now_is_database_unavailable() -> None:
    error = _operational_error_with_sqlstate("57P03")

    assert is_database_unavailable_error(error) is True


def test_postgresql_serialization_failure_is_not_database_unavailable() -> None:
    error = _operational_error_with_sqlstate("40001")

    assert is_database_unavailable_error(error) is False


def test_postgresql_invalid_password_is_not_database_unavailable() -> None:
    error = _operational_error_with_sqlstate("28P01")

    assert is_database_unavailable_error(error) is False


def test_psycopg_connection_attempt_without_sqlstate_is_database_unavailable() -> None:
    original = RuntimeError("connection refused")
    original.pgconn = object()  # type: ignore[attr-defined]
    error = OperationalError(None, {}, original)

    assert is_database_unavailable_error(error) is True


def test_sqlite_cantopen_is_database_unavailable(tmp_path) -> None:
    runtime = create_database_runtime(f"sqlite:///{tmp_path}")
    try:
        with pytest.raises(OperationalError) as exc_info:
            with runtime.session_factory() as db:
                db.execute(text("SELECT 1"))

        error = exc_info.value
        sqlite_errorcode = getattr(error.orig, "sqlite_errorcode", None)
        assert error.statement is None
        assert sqlite_errorcode == sqlite3.SQLITE_CANTOPEN
        assert is_database_unavailable_error(error) is True
    finally:
        runtime.dispose()
