from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.session import is_database_unavailable_error


def test_integrity_error_without_statement_is_not_database_unavailable() -> None:
    error = IntegrityError(
        None,
        {},
        RuntimeError("deferred foreign key violation"),
    )

    assert is_database_unavailable_error(error) is False


def test_postgresql_connection_sqlstate_is_database_unavailable() -> None:
    original = RuntimeError("connection failure")
    original.sqlstate = "08006"  # type: ignore[attr-defined]
    error = OperationalError(None, {}, original)

    assert is_database_unavailable_error(error) is True


def test_postgresql_serialization_failure_is_not_database_unavailable() -> None:
    original = RuntimeError("serialization failure")
    original.sqlstate = "40001"  # type: ignore[attr-defined]
    error = OperationalError(None, {}, original)

    assert is_database_unavailable_error(error) is False
