import shutil
import sqlite3
from pathlib import Path
from threading import Event, Thread

import pytest
from sqlalchemy import text

import app.models  # noqa: F401 - register model metadata for legacy schema tests
from app.db.session import (
    Base,
    DatabaseRuntimeUnavailableError,
    create_database_runtime,
    initialize_database,
    migrate_database,
)
from app.services import database_management
from app.services.database_management import (
    DatabaseRestoreError,
    InvalidDatabaseBackupError,
    create_sqlite_backup,
    restore_sqlite_database,
    stage_sqlite_restore_upload,
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


def test_restore_rejects_conflict_policy_moved_between_constraints(
    tmp_path: Path,
) -> None:
    runtime = _initialized_runtime(tmp_path)
    live_path = tmp_path / "sokora.db"
    backup_path: Path | None = None
    candidate = tmp_path / "conflict-policy-mismatch.db"
    try:
        with sqlite3.connect(live_path) as db:
            db.execute(
                """
                CREATE TABLE conflict_policy_probe (
                    id INTEGER PRIMARY KEY,
                    first_value TEXT UNIQUE ON CONFLICT IGNORE,
                    second_value TEXT UNIQUE ON CONFLICT REPLACE
                )
                """
            )
            db.commit()

        backup_path = create_sqlite_backup(runtime)
        shutil.copy2(backup_path, candidate)

        with sqlite3.connect(candidate) as db:
            row = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'conflict_policy_probe'"
            ).fetchone()
            assert row is not None and row[0] is not None
            table_sql = str(row[0])
            changed_sql = table_sql.replace(
                "first_value TEXT UNIQUE ON CONFLICT IGNORE",
                "first_value TEXT UNIQUE ON CONFLICT REPLACE",
            ).replace(
                "second_value TEXT UNIQUE ON CONFLICT REPLACE",
                "second_value TEXT UNIQUE ON CONFLICT IGNORE",
            )
            assert changed_sql != table_sql

            db.execute("PRAGMA writable_schema = ON")
            db.execute(
                "UPDATE sqlite_master SET sql = ? "
                "WHERE type = 'table' AND name = 'conflict_policy_probe'",
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


def test_restore_rejects_partial_index_predicate_mismatch(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    live_path = tmp_path / "sokora.db"
    backup_path: Path | None = None
    candidate = tmp_path / "partial-index-mismatch.db"
    index_name = "idx_groups_name_partial_probe"
    try:
        with sqlite3.connect(live_path) as db:
            db.execute(
                f"CREATE INDEX {index_name} ON groups(name) WHERE id > 0"
            )
            db.commit()

        backup_path = create_sqlite_backup(runtime)
        shutil.copy2(backup_path, candidate)

        with sqlite3.connect(candidate) as db:
            db.execute(f"DROP INDEX {index_name}")
            db.execute(
                f"CREATE INDEX {index_name} ON groups(name) WHERE id > 1"
            )
            db.commit()

        with pytest.raises(InvalidDatabaseBackupError, match="schema"):
            validate_sqlite_restore_candidate(candidate, runtime)
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)


def test_restore_rejects_expression_index_mismatch(tmp_path: Path) -> None:
    runtime = _initialized_runtime(tmp_path)
    live_path = tmp_path / "sokora.db"
    backup_path: Path | None = None
    candidate = tmp_path / "expression-index-mismatch.db"
    index_name = "idx_groups_name_expression_probe"
    try:
        with sqlite3.connect(live_path) as db:
            db.execute(f"CREATE INDEX {index_name} ON groups(lower(name))")
            db.commit()

        backup_path = create_sqlite_backup(runtime)
        shutil.copy2(backup_path, candidate)

        with sqlite3.connect(candidate) as db:
            db.execute(f"DROP INDEX {index_name}")
            db.execute(f"CREATE INDEX {index_name} ON groups(upper(name))")
            db.commit()

        with pytest.raises(InvalidDatabaseBackupError, match="schema"):
            validate_sqlite_restore_candidate(candidate, runtime)
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)


def test_restore_accepts_equivalent_adopted_create_all_schema(tmp_path: Path) -> None:
    fresh_runtime = _initialized_runtime(tmp_path)
    fresh_path = tmp_path / "sokora.db"
    legacy_path = tmp_path / "legacy.db"
    legacy_runtime = create_database_runtime(f"sqlite:///{legacy_path}")

    try:
        # Reproduce a pre-#54 database, then run the supported Alembic adoption
        # path. SQLite batch migration retains quoting around custom_holidays
        # even though the resulting structure and constraints match fresh DBs.
        Base.metadata.create_all(bind=legacy_runtime.engine)
        migrate_database(legacy_runtime)

        with (
            sqlite3.connect(fresh_path) as fresh,
            sqlite3.connect(legacy_path) as legacy,
        ):
            fresh_sql = fresh.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'custom_holidays'"
            ).fetchone()
            legacy_sql = legacy.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'custom_holidays'"
            ).fetchone()
        assert fresh_sql is not None and legacy_sql is not None
        assert fresh_sql[0] != legacy_sql[0]

        validate_sqlite_restore_candidate(legacy_path, fresh_runtime)
    finally:
        legacy_runtime.dispose()
        fresh_runtime.dispose()


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


def test_restore_rollback_blocks_requests_until_previous_database_is_recovered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    staged_path: Path | None = None
    rollback_started = Event()
    rollback_release = Event()
    restore_done = Event()
    request_entered = Event()
    restore_errors: list[BaseException] = []
    observed_names: list[str] = []
    restore_thread: Thread | None = None
    request_thread: Thread | None = None

    try:
        with runtime.session_factory() as db:
            row = db.execute(
                text("select id, name from groups order by id limit 1")
            ).one()
            group_id = int(row.id)
            original_name = str(row.name)

        backup_path = create_sqlite_backup(runtime)
        with sqlite3.connect(backup_path) as candidate:
            candidate.execute(
                "update groups set name = ? where id = ?",
                ("candidate-value", group_id),
            )
            candidate.commit()

        with backup_path.open("rb") as source:
            staged_path = stage_sqlite_restore_upload(source, runtime)

        original_verify = database_management._verify_rebound_runtime
        verify_calls = 0

        def fail_first_rebound_verification(runtime_to_verify) -> None:
            nonlocal verify_calls
            verify_calls += 1
            if verify_calls == 1:
                raise RuntimeError("forced post-replacement failure")
            original_verify(runtime_to_verify)

        original_replace = database_management.os.replace
        replace_calls = 0

        def block_rollback_replace(source, destination) -> None:
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                rollback_started.set()
                if not rollback_release.wait(timeout=2):
                    raise RuntimeError("rollback release timed out")
            original_replace(source, destination)

        monkeypatch.setattr(
            database_management,
            "_verify_rebound_runtime",
            fail_first_rebound_verification,
        )
        monkeypatch.setattr(database_management.os, "replace", block_rollback_replace)

        def run_restore() -> None:
            try:
                assert staged_path is not None
                restore_sqlite_database(runtime, staged_path)
            except BaseException as exc:
                restore_errors.append(exc)
            finally:
                restore_done.set()

        def run_request() -> None:
            with runtime.managed_session() as db:
                request_entered.set()
                name = db.scalar(
                    text("select name from groups where id = :group_id"),
                    {"group_id": group_id},
                )
                observed_names.append(str(name))

        restore_thread = Thread(target=run_restore, daemon=True)
        restore_thread.start()
        assert rollback_started.wait(timeout=2)

        request_thread = Thread(target=run_request, daemon=True)
        request_thread.start()
        assert not request_entered.wait(timeout=0.1)

        rollback_release.set()
        assert restore_done.wait(timeout=2)
        restore_thread.join(timeout=1)
        request_thread.join(timeout=2)

        assert len(restore_errors) == 1
        assert isinstance(restore_errors[0], DatabaseRestoreError)
        assert request_entered.is_set()
        assert observed_names == [original_name]
    finally:
        rollback_release.set()
        if restore_thread is not None:
            restore_thread.join(timeout=1)
        if request_thread is not None:
            request_thread.join(timeout=1)
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)


def test_restore_double_failure_fences_runtime_and_preserves_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _initialized_runtime(tmp_path)
    backup_path: Path | None = None
    staged_path: Path | None = None
    preserved_snapshot: Path | None = None

    try:
        backup_path = create_sqlite_backup(runtime)
        with backup_path.open("rb") as source:
            staged_path = stage_sqlite_restore_upload(source, runtime)

        original_verify = database_management._verify_rebound_runtime
        verify_calls = 0

        def fail_first_rebound_verification(runtime_to_verify) -> None:
            nonlocal verify_calls
            verify_calls += 1
            if verify_calls == 1:
                raise RuntimeError("forced post-replacement failure")
            original_verify(runtime_to_verify)

        original_replace = database_management.os.replace
        replace_calls = 0

        def fail_rollback_replace(source, destination) -> None:
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 2:
                raise OSError("forced rollback failure")
            original_replace(source, destination)

        monkeypatch.setattr(
            database_management,
            "_verify_rebound_runtime",
            fail_first_rebound_verification,
        )
        monkeypatch.setattr(database_management.os, "replace", fail_rollback_replace)

        assert staged_path is not None
        with pytest.raises(
            DatabaseRestoreError, match="手動復旧用snapshot"
        ) as exc_info:
            restore_sqlite_database(runtime, staged_path)

        snapshots = list(tmp_path.glob(".sokora.db.rollback-*.db"))
        assert len(snapshots) == 1
        preserved_snapshot = snapshots[0]
        assert str(preserved_snapshot.resolve()) in str(exc_info.value)

        with sqlite3.connect(preserved_snapshot) as snapshot:
            assert snapshot.execute("PRAGMA integrity_check").fetchone() == ("ok",)

        assert runtime.unavailable_reason is not None
        with pytest.raises(DatabaseRuntimeUnavailableError):
            with runtime.managed_session():
                pass
        with pytest.raises(DatabaseRuntimeUnavailableError):
            with runtime.exclusive_maintenance():
                pass
    finally:
        runtime.dispose()
        if backup_path is not None:
            backup_path.unlink(missing_ok=True)
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        if preserved_snapshot is not None:
            preserved_snapshot.unlink(missing_ok=True)
