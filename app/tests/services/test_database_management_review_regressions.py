import shutil
import sqlite3
from pathlib import Path
from threading import Event, Thread

import pytest

from app.db.session import create_database_runtime, initialize_database
from app.services.database_management import (
    InvalidDatabaseBackupError,
    create_sqlite_backup,
    validate_sqlite_restore_candidate,
)


def _initialized_runtime(tmp_path: Path):
    database_path = tmp_path / "sokora.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    initialize_database(runtime)
    return runtime


def test_restore_rejects_table_constraint_definition_mismatch(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    candidate = tmp_path / "constraint-mismatch.db"
    try:
        backup_path = create_sqlite_backup(runtime)
        shutil.copy2(backup_path, candidate)

        with sqlite3.connect(candidate) as db:
            row = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'groups'"
            ).fetchone()
            assert row is not None and row[0] is not None
            table_sql = str(row[0]).rstrip()
            assert table_sql.endswith(")")
            changed_sql = table_sql[:-1] + ", CHECK (1 = 1))"

            db.execute("PRAGMA writable_schema = ON")
            db.execute(
                "UPDATE sqlite_master SET sql = ? "
                "WHERE type = 'table' AND name = 'groups'",
                (changed_sql,),
            )
            db.execute("PRAGMA writable_schema = OFF")
            db.commit()

        with pytest.raises(InvalidDatabaseBackupError, match="schema"):
            validate_sqlite_restore_candidate(candidate, runtime)
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)


def test_session_close_failure_does_not_block_future_maintenance() -> None:
    runtime = create_database_runtime("sqlite:///:memory:")
    original_factory = runtime.session_factory
    maintenance_entered = Event()

    class CloseFailingSession:
        def close(self) -> None:
            raise RuntimeError("close failed")

    def enter_maintenance() -> None:
        with runtime.exclusive_maintenance():
            maintenance_entered.set()

    try:
        runtime.session_factory = lambda: CloseFailingSession()  # type: ignore[assignment]
        with pytest.raises(RuntimeError, match="close failed"):
            with runtime.managed_session():
                pass

        maintenance_thread = Thread(target=enter_maintenance, daemon=True)
        maintenance_thread.start()
        assert maintenance_entered.wait(timeout=1)
    finally:
        runtime.session_factory = original_factory
        runtime.dispose()
