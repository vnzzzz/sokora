"""管理者向けSQLite backup/restoreのvalidation・consistency・recovery境界。

HTTP upload/downloadやauthorizationはrouterが担当し、このmoduleはfile-backed SQLiteだけを
対象に、online backup、restore candidate validation、atomic replacement、rollback/recoveryを
orchestrateする。schemaのsemantic signature構築は ``sqlite_schema`` moduleが担当する。

restore前validationはmaintenance modeへ入る前に完了させ、live DBを書き換えない。実際の
replacementでは :class:`DatabaseRuntime` のexclusive maintenanceを使ってrequest sessionを
drainし、新connectionが開かない区間でengine/file/sidecarを切り替える。
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO

from app.core.config import logger
from app.db.session import DatabaseRuntime, alembic_heads, sqlite_database_path
from app.services.errors import ApplicationError
from app.services.sqlite_schema import schema_signature

_SQLITE_HEADER = b"SQLite format 3\x00"
_COPY_CHUNK_SIZE = 1024 * 1024


class DatabaseManagementError(ApplicationError):
    """DB管理operationでadapterが扱えるapplication-level error。

    raw sqlite3/OS exceptionはcauseとして保持し、利用者向けdetailへそのまま変換しない。
    automatic rollbackまで失敗した場合のrecovery snapshot pathなど、operator actionに必要な
    情報だけはsubclassが意図的にdetailへ含めることがある。
    """


class UnsupportedDatabaseBackendError(DatabaseManagementError):
    """file-backed SQLite以外へSQLite固有operationを要求したことを表す。

    PostgreSQLやin-memory SQLiteへfile copy/replaceを誤適用しないためのbackend guard。
    """

    status_code = 409


class InvalidDatabaseBackupError(DatabaseManagementError):
    """SQLite fileのintegrity/互換性validationが成立しないことを表す。

    主にupload candidateのreplacement前検査で使うほか、生成したonline backup自身の
    integrity確認にも利用する。restore candidate検査から送出される場合、live DB replacementは
    まだ開始していない。
    """

    status_code = 400


class DatabaseRestoreError(DatabaseManagementError):
    """validated candidateの適用または適用後recoveryが安全に完了できないことを表す。

    automatic rollbackまで失敗した場合、runtimeはfail-closedへfenceされ、このerrorの
    messageはoperator actionが必要であることを示す。
    """

    status_code = 500


def require_sqlite_database_path(runtime: DatabaseRuntime) -> Path:
    """runtime URLから管理対象となるlive SQLite file pathを確定する。

    file pathを持たないin-memory SQLiteやPostgreSQLはここで拒否し、後続処理がfilesystem
    operationをbackend判定なしで実行できるようにする。返すpathの存在確認はoperationごとに
    必要条件が異なるため、このfunctionでは行わない。
    """

    path = sqlite_database_path(runtime.database_url)
    if path is None:
        raise UnsupportedDatabaseBackendError(
            "データベース管理はファイルベースSQLiteでのみ利用できます。"
        )
    return path


def _readonly_connection(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


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


def validate_sqlite_restore_candidate(
    candidate_path: Path,
    runtime: DatabaseRuntime,
) -> None:
    """candidateをread-onlyで検査し、current live DBとrestore互換であることを保証する。

    replacement前にSQLite header、integrity/FK、Alembic head、semantic schemaを検証する。
    古いrevisionをrestore時にmigrationしたり、未知schemaを「近い」と推測したりしない。
    current sokoraが現在利用しているschemaと一致するcandidateだけを許可する。

    このfunctionはmaintenance modeへ入らずlive DBを書き換えないため、validation failure時に
    rollbackは不要である。
    """

    live_path = require_sqlite_database_path(runtime)
    if not candidate_path.is_file():
        raise InvalidDatabaseBackupError(
            "アップロードされたDBファイルを確認できません。"
        )

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
            candidate_schema = schema_signature(candidate)

        with _readonly_connection(live_path) as live:
            live_schema = schema_signature(live)
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
        with (
            _readonly_connection(source_path) as source,
            sqlite3.connect(target_path) as target,
        ):
            source.backup(target)
            target.commit()
    except sqlite3.DatabaseError as exc:
        raise DatabaseManagementError("SQLite backupの作成に失敗しました。") from exc


def create_sqlite_backup(runtime: DatabaseRuntime) -> Path:
    """online SQLite backup APIでconsistent snapshotを作り、一時file pathを返す。

    snapshot中はruntimeのshared session countへ参加し、exclusive restoreが同時にlive fileを
    replaceしないようにする。作成後にsnapshot自身のintegrity/FKを検証する。

    返されたtemporary fileのownershipはcallerへ移り、download完了等の適切な時点でcallerが
    削除する。失敗時だけこのfunctionが作成fileをcleanupする。
    """

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
    """upload streamをlive DBと同じdirectoryへdurableなstaged fileとして保存する。

    staged fileを同一filesystemへ置くのは後続の``os.replace``をatomic renameとして成立
    させるためである。copy後はfileをflush/fsyncし、空uploadをrejectする。

    返却後のstaged fileはrestore callerのownershipとなり、成功/失敗にかかわらず最終cleanup
    する。validation前にlive DBへ触れることはない。
    """

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
            raise InvalidDatabaseBackupError("空のファイルはリストアできません。")
        return staged_path
    except Exception:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        raise


def _remove_sqlite_sidecars(database_path: Path) -> None:
    for suffix in ("-wal", "-shm", "-journal"):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)


def _sync_directory(path: Path) -> None:
    """atomic rename後のdirectory entryをbest-effortでdurable化する。

    platform/filesystemによってdirectory fsyncを利用できない場合はrestore自体を失敗扱いに
    しない。file contentのdurabilityはstaging/SQLite backup側で別途確保する。
    """

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
    is created, SQLAlchemy connections are disposed, the staged database is
    atomically moved into place, and stale SQLite sidecars are removed. Any
    recovery and connection reinitialization also complete before requests are
    admitted again.
    """

    live_path = require_sqlite_database_path(runtime)
    rollback_path: Path | None = None
    replaced = False
    engine_disposed = False

    validate_sqlite_restore_candidate(staged_path, runtime)
    try:
        with runtime.exclusive_maintenance():
            try:
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
                        preserved_snapshot: Path | None = None
                        if rollback_path is not None and rollback_path.exists():
                            preserved_snapshot = rollback_path.resolve()
                            # The snapshot is now an operator recovery artifact.
                            # Do not let the outer cleanup remove it.
                            rollback_path = None

                        runtime.mark_unavailable(
                            "SQLite restore recovery failed; restart and manual recovery are required"
                        )
                        logger.critical(
                            "SQLite restore and automatic rollback both failed; "
                            "runtime fenced; recovery snapshot=%s",
                            preserved_snapshot,
                            exc_info=True,
                        )

                        message = (
                            "リストアと自動ロールバックに失敗したためDBアクセスを停止しました。"
                            "サービスを停止し、手動復旧後に再起動してください。"
                        )
                        if preserved_snapshot is not None:
                            message += f" 手動復旧用snapshot: {preserved_snapshot}"
                        raise DatabaseRestoreError(message) from rollback_exc
                elif engine_disposed:
                    try:
                        runtime.recreate_connections()
                    except Exception as recreate_exc:
                        runtime.mark_unavailable(
                            "Database connection recovery failed; restart is required"
                        )
                        logger.critical(
                            "Failed to recreate database connections after restore failure; "
                            "runtime fenced",
                            exc_info=True,
                        )
                        raise DatabaseRestoreError(
                            "DB接続の再初期化に失敗したためDBアクセスを停止しました。"
                            "サービス再起動が必要です。"
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
