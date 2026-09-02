"""Safe SQLite backup and restore operations for the administrator UI."""

from __future__ import annotations

import os
import shutil
import sqlite3
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO, NamedTuple

from app.core.config import logger
from app.db.session import DatabaseRuntime, alembic_heads, sqlite_database_path
from app.services.errors import ApplicationError

_SQLITE_HEADER = b"SQLite format 3\x00"
_COPY_CHUNK_SIZE = 1024 * 1024


class DatabaseManagementError(ApplicationError):
    """Base error for database administration operations."""


class UnsupportedDatabaseBackendError(DatabaseManagementError):
    """The configured backend cannot be managed through the SQLite UI."""

    status_code = 409


class InvalidDatabaseBackupError(DatabaseManagementError):
    """An uploaded database failed validation."""

    status_code = 400


class DatabaseRestoreError(DatabaseManagementError):
    """A validated restore could not be applied safely."""

    status_code = 500


class _TableSchema(NamedTuple):
    columns: tuple[tuple[object, ...], ...]
    foreign_keys: tuple[tuple[object, ...], ...]
    indexes: tuple[tuple[object, ...], ...]


class _SchemaSignature(NamedTuple):
    tables: tuple[tuple[str, _TableSchema], ...]
    views_and_triggers: tuple[tuple[object, ...], ...]


def require_sqlite_database_path(runtime: DatabaseRuntime) -> Path:
    """Return the live file path or reject non-file-backed SQLite backends."""

    path = sqlite_database_path(runtime.database_url)
    if path is None:
        raise UnsupportedDatabaseBackendError(
            "データベース管理はファイルベースSQLiteでのみ利用できます。"
        )
    return path


def _readonly_connection(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _integrity_check(connection: sqlite3.Connection) -> None:
    integrity_rows = [
        str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()
    ]
    if integrity_rows != ["ok"]:
        raise InvalidDatabaseBackupError(
            "SQLite integrity checkに失敗したためリストアできません。"
        )

    foreign_key_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_rows:
        raise InvalidDatabaseBackupError(
            "外部キー整合性に問題があるためリストアできません。"
        )


def _alembic_revisions(connection: sqlite3.Connection) -> set[str]:
    try:
        rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    except sqlite3.DatabaseError as exc:
        raise InvalidDatabaseBackupError(
            "Alembic revisionを確認できないデータベースです。"
        ) from exc
    return {str(row[0]) for row in rows}


def _schema_signature(connection: sqlite3.Connection) -> _SchemaSignature:
    table_names = [
        str(row[0])
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]

    tables: list[tuple[str, _TableSchema]] = []
    for table_name in table_names:
        quoted_table = _quote_identifier(table_name)
        columns = tuple(
            tuple(row[1:])
            for row in connection.execute(
                f"PRAGMA table_xinfo({quoted_table})"
            ).fetchall()
        )
        foreign_keys = tuple(
            tuple(row[2:])
            for row in connection.execute(
                f"PRAGMA foreign_key_list({quoted_table})"
            ).fetchall()
        )

        indexes: list[tuple[object, ...]] = []
        for index_row in connection.execute(
            f"PRAGMA index_list({quoted_table})"
        ).fetchall():
            index_name = str(index_row[1])
            quoted_index = _quote_identifier(index_name)
            index_columns = tuple(
                tuple(row[1:])
                for row in connection.execute(
                    f"PRAGMA index_xinfo({quoted_index})"
                ).fetchall()
            )
            # Index names are implementation details for SQLite auto-indexes.
            indexes.append(
                (
                    bool(index_row[2]),
                    str(index_row[3]),
                    bool(index_row[4]),
                    index_columns,
                )
            )

        tables.append(
            (
                table_name,
                _TableSchema(
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=tuple(sorted(indexes, key=repr)),
                ),
            )
        )

    views_and_triggers = tuple(
        tuple(row)
        for row in connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE type IN ('view', 'trigger')
            ORDER BY type, name
            """
        ).fetchall()
    )
    return _SchemaSignature(
        tables=tuple(tables),
        views_and_triggers=views_and_triggers,
    )


def validate_sqlite_restore_candidate(
    candidate_path: Path,
    runtime: DatabaseRuntime,
) -> None:
    """Validate file format, integrity, revision, and schema before replacement."""

    live_path = require_sqlite_database_path(runtime)
    if not candidate_path.is_file():
        raise InvalidDatabaseBackupError("アップロードされたDBファイルを確認できません。")

    try:
        with candidate_path.open("rb") as candidate_file:
            if candidate_file.read(len(_SQLITE_HEADER)) != _SQLITE_HEADER:
                raise InvalidDatabaseBackupError(
                    "SQLiteデータベースではないファイルはリストアできません。"
                )
    except OSError as exc:
        raise InvalidDatabaseBackupError(
            "アップロードされたDBファイルを読み取れません。"
        ) from exc

    try:
        with _readonly_connection(candidate_path) as candidate:
            _integrity_check(candidate)
            candidate_revisions = _alembic_revisions(candidate)
            expected_revisions = set(alembic_heads())
            if candidate_revisions != expected_revisions:
                raise InvalidDatabaseBackupError(
                    "現在のsokoraとAlembic revisionが一致しないDBはリストアできません。"
                )
            candidate_schema = _schema_signature(candidate)

        with _readonly_connection(live_path) as live:
            live_schema = _schema_signature(live)
    except InvalidDatabaseBackupError:
        raise
    except sqlite3.DatabaseError as exc:
        raise InvalidDatabaseBackupError(
            "SQLiteデータベースとして検証できないファイルです。"
        ) from exc

    if candidate_schema != live_schema:
        raise InvalidDatabaseBackupError(
            "現在のsokoraとDB schemaが一致しないためリストアできません。"
        )


def _backup_database(source_path: Path, target_path: Path) -> None:
    try:
        with _readonly_connection(source_path) as source, sqlite3.connect(
            target_path
        ) as target:
            source.backup(target)
            target.commit()
    except sqlite3.DatabaseError as exc:
        raise DatabaseManagementError(
            "SQLite backupの作成に失敗しました。"
        ) from exc


def create_sqlite_backup(runtime: DatabaseRuntime) -> Path:
    """Create a consistent online backup and return its temporary path."""

    source_path = require_sqlite_database_path(runtime)
    if not source_path.is_file():
        raise DatabaseManagementError("SQLiteデータベースファイルが存在しません。")

    with tempfile.NamedTemporaryFile(
        prefix="sokora-backup-",
        suffix=".db",
        delete=False,
    ) as temporary:
        backup_path = Path(temporary.name)

    try:
        # Participate in the runtime's shared-access count so an exclusive
        # restore cannot replace the file while a backup snapshot is running.
        with runtime.managed_session():
            _backup_database(source_path, backup_path)
        with _readonly_connection(backup_path) as backup:
            _integrity_check(backup)
        return backup_path
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise


def stage_sqlite_restore_upload(
    source: BinaryIO,
    runtime: DatabaseRuntime,
) -> Path:
    """Copy an uploaded DB into the live DB directory for atomic replacement."""

    live_path = require_sqlite_database_path(runtime)
    live_path.parent.mkdir(parents=True, exist_ok=True)

    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=live_path.parent,
            prefix=f".{live_path.name}.restore-",
            suffix=".db",
            delete=False,
        ) as staged:
            staged_path = Path(staged.name)
            shutil.copyfileobj(source, staged, length=_COPY_CHUNK_SIZE)
            staged.flush()
            os.fsync(staged.fileno())

        if staged_path.stat().st_size == 0:
            raise InvalidDatabaseBackupError(
                "空のファイルはリストアできません。"
            )
        return staged_path
    except Exception:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        raise


def _remove_sqlite_sidecars(database_path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)


def _sync_directory(path: Path) -> None:
    """Best-effort fsync of the containing directory after atomic replacement."""

    try:
        directory_fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def _verify_rebound_runtime(runtime: DatabaseRuntime) -> None:
    expected_revisions = set(alembic_heads())
    with runtime.engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
        rows = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).fetchall()
    if {str(row[0]) for row in rows} != expected_revisions:
        raise RuntimeError("restored database revision changed during replacement")


def restore_sqlite_database(
    runtime: DatabaseRuntime,
    staged_path: Path,
) -> None:
    """Atomically replace the live SQLite DB after draining request sessions.

    The candidate is validated before entering maintenance mode. During the
    exclusive section existing request sessions are drained, a rollback backup
    is created, SQLAlchemy connections are disposed, SQLite sidecars are
    removed, and the staged file is atomically moved into place. Any failure
    after replacement attempts to restore the pre-operation backup before
    requests are admitted again.
    """

    live_path = require_sqlite_database_path(runtime)
    rollback_path: Path | None = None
    replaced = False
    engine_disposed = False

    try:
        validate_sqlite_restore_candidate(staged_path, runtime)
        with runtime.exclusive_maintenance():
            with tempfile.NamedTemporaryFile(
                dir=live_path.parent,
                prefix=f".{live_path.name}.rollback-",
                suffix=".db",
                delete=False,
            ) as rollback_file:
                rollback_path = Path(rollback_file.name)

            _backup_database(live_path, rollback_path)
            live_mode = stat.S_IMODE(live_path.stat().st_mode)
            os.chmod(staged_path, live_mode)

            runtime.engine.dispose()
            engine_disposed = True
            os.replace(staged_path, live_path)
            replaced = True

            # Old WAL/SHM files belong to the database that was just replaced.
            # Remove them only after os.replace succeeds, while maintenance
            # mode still prevents any new SQLite connection from opening.
            _remove_sqlite_sidecars(live_path)
            _sync_directory(live_path.parent)

            runtime.recreate_connections()
            engine_disposed = False
            _verify_rebound_runtime(runtime)

            rollback_path.unlink(missing_ok=True)
            rollback_path = None
    except Exception as exc:
        if replaced and rollback_path is not None and rollback_path.exists():
            try:
                runtime.engine.dispose()
                _remove_sqlite_sidecars(live_path)
                os.replace(rollback_path, live_path)
                rollback_path = None
                _sync_directory(live_path.parent)
                runtime.recreate_connections()
                engine_disposed = False
                _verify_rebound_runtime(runtime)
                logger.error(
                    "SQLite restore failed after replacement; previous DB restored",
                    exc_info=True,
                )
            except Exception as rollback_exc:
                logger.critical(
                    "SQLite restore and automatic rollback both failed",
                    exc_info=True,
                )
                raise DatabaseRestoreError(
                    "リストアと自動ロールバックに失敗しました。"
                    "サービスを停止し、運用バックアップから手動復旧してください。"
                ) from rollback_exc
        elif engine_disposed:
            try:
                runtime.recreate_connections()
            except Exception as recreate_exc:
                logger.critical(
                    "Failed to recreate database connections after restore failure",
                    exc_info=True,
                )
                raise DatabaseRestoreError(
                    "DB接続の再初期化に失敗しました。サービス再起動が必要です。"
                ) from recreate_exc

        if isinstance(exc, DatabaseManagementError):
            raise
        raise DatabaseRestoreError(
            "リストアに失敗したため、変更は適用されませんでした。"
        ) from exc
    finally:
        staged_path.unlink(missing_ok=True)
        if rollback_path is not None:
            rollback_path.unlink(missing_ok=True)
