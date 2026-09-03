import shutil
import sqlite3
from pathlib import Path
from threading import Event, Thread
from time import sleep

import pytest
from sqlalchemy import text

from app.db.session import create_database_runtime, initialize_database
from app.services.database_management import (
    InvalidDatabaseBackupError,
    UnsupportedDatabaseBackendError,
    create_sqlite_backup,
    require_sqlite_database_path,
    restore_sqlite_database,
    stage_sqlite_restore_upload,
    validate_sqlite_restore_candidate,
)


def _initialized_runtime(tmp_path: Path):
    database_path = tmp_path / "sokora.db"
    runtime = create_database_runtime(f"sqlite:///{database_path}")
    initialize_database(runtime)
    return runtime


def test_sqlite_backup_contains_consistent_schema_and_data(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    try:
        with runtime.session_factory() as db:
            expected_groups = db.scalar(text("select count(*) from groups"))

        backup_path = create_sqlite_backup(runtime)

        with sqlite3.connect(backup_path) as backup:
            assert backup.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert backup.execute("select count(*) from groups").fetchone() == (
                expected_groups,
            )
            assert backup.execute("select version_num from alembic_version").fetchone()
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)


def test_restore_rejects_non_sqlite_file_without_touching_live_db(
    tmp_path: Path,
) -> None:
    runtime = _initialized_runtime(tmp_path)
    candidate = tmp_path / "invalid.db"
    candidate.write_bytes(b"not a sqlite database")

    try:
        with runtime.session_factory() as db:
            before = db.scalar(text("select count(*) from groups"))

        with pytest.raises(InvalidDatabaseBackupError, match="SQLite"):
            validate_sqlite_restore_candidate(candidate, runtime)

        with runtime.session_factory() as db:
            assert db.scalar(text("select count(*) from groups")) == before
    finally:
        runtime.dispose()


def test_restore_rejects_wrong_alembic_revision(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    candidate = tmp_path / "candidate.db"
    try:
        backup_path = create_sqlite_backup(runtime)
        shutil.copy2(backup_path, candidate)
        with sqlite3.connect(candidate) as db:
            db.execute("update alembic_version set version_num = 'old-revision'")
            db.commit()

        with pytest.raises(InvalidDatabaseBackupError, match="Alembic revision"):
            validate_sqlite_restore_candidate(candidate, runtime)
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)


def test_restore_rejects_schema_mismatch(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    candidate = tmp_path / "candidate.db"
    try:
        backup_path = create_sqlite_backup(runtime)
        shutil.copy2(backup_path, candidate)
        with sqlite3.connect(candidate) as db:
            db.execute("create table unexpected_table (id integer primary key)")
            db.commit()

        with pytest.raises(InvalidDatabaseBackupError, match="schema"):
            validate_sqlite_restore_candidate(candidate, runtime)
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)


def test_restore_replaces_data_and_recreates_connections(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    staged_path: Path | None = None
    try:
        with runtime.session_factory() as db:
            row = db.execute(
                text("select id, name from groups order by id limit 1")
            ).one()
            group_id = int(row.id)
            original_name = str(row.name)

        backup_path = create_sqlite_backup(runtime)

        with runtime.session_factory() as db:
            db.execute(
                text("update groups set name = :name where id = :group_id"),
                {"name": "changed-after-backup", "group_id": group_id},
            )
            db.commit()

        with backup_path.open("rb") as source:
            staged_path = stage_sqlite_restore_upload(source, runtime)

        old_engine = runtime.engine
        restore_sqlite_database(runtime, staged_path)

        assert runtime.engine is not old_engine
        with runtime.session_factory() as db:
            restored_name = db.scalar(
                text("select name from groups where id = :group_id"),
                {"group_id": group_id},
            )
        assert restored_name == original_name
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)


def test_database_runtime_drains_request_sessions_before_maintenance(
    tmp_path: Path,
) -> None:
    runtime = _initialized_runtime(tmp_path)
    session_open = Event()
    release_session = Event()
    maintenance_entered = Event()

    def hold_session() -> None:
        with runtime.managed_session():
            session_open.set()
            release_session.wait(timeout=5)

    def enter_maintenance() -> None:
        with runtime.exclusive_maintenance():
            maintenance_entered.set()

    session_thread = Thread(target=hold_session)
    maintenance_thread = Thread(target=enter_maintenance)
    try:
        session_thread.start()
        assert session_open.wait(timeout=2)

        maintenance_thread.start()
        sleep(0.05)
        assert not maintenance_entered.is_set()

        release_session.set()
        assert maintenance_entered.wait(timeout=2)
    finally:
        release_session.set()
        session_thread.join(timeout=2)
        maintenance_thread.join(timeout=2)
        runtime.dispose()


def test_memory_sqlite_is_not_available_for_file_restore() -> None:
    runtime = create_database_runtime("sqlite:///:memory:")
    try:
        with pytest.raises(UnsupportedDatabaseBackendError):
            require_sqlite_database_path(runtime)
    finally:
        runtime.dispose()
