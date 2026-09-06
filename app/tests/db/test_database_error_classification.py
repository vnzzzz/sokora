from sqlalchemy.exc import IntegrityError, OperationalError

from app.db.session import is_database_unavailable_error


def test_integrity_error_without_statement_is_not_database_unavailable() -> None:
    error = IntegrityError(
        None,
        {},
        RuntimeError("deferred foreign key violation"),
    )

    assert is_database_unavailable_error(error) is False


def test_connection_operational_error_is_database_unavailable() -> None:
    error = OperationalError(
        None,
        {},
        RuntimeError("could not open database"),
    )

    assert is_database_unavailable_error(error) is True
