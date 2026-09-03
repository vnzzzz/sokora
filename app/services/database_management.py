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


class _IndexSchema(NamedTuple):
    unique: bool
    partial: bool
    columns: tuple[tuple[object, ...], ...]
    predicate: str | None
    expression: str | None


class _TableSchema(NamedTuple):
    columns: tuple[tuple[object, ...], ...]
    foreign_keys: tuple[tuple[object, ...], ...]
    indexes: tuple[_IndexSchema, ...]
    definition: str
    conflict_policies: tuple[tuple[str, str], ...]


class _SchemaSignature(NamedTuple):
    tables: tuple[tuple[str, _TableSchema], ...]
    views_and_triggers: tuple[tuple[str, str, str, str], ...]


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


def _sql_tokens(sql: str) -> tuple[str, ...]:
    """Tokenize SQLite DDL while normalizing presentation-only differences."""

    tokens: list[str] = []
    index = 0
    length = len(sql)

    while index < length:
        char = sql[index]
        if char.isspace():
            index += 1
            continue

        if char == "'":
            start = index
            index += 1
            while index < length:
                if sql[index] == "'":
                    if index + 1 < length and sql[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            tokens.append(sql[start:index])
            continue

        if char in {'"', "`", "["}:
            closing = "]" if char == "[" else char
            index += 1
            identifier: list[str] = []
            while index < length:
                current = sql[index]
                if current == closing:
                    if index + 1 < length and sql[index + 1] == closing:
                        identifier.append(closing)
                        index += 2
                        continue
                    index += 1
                    break
                identifier.append(current)
                index += 1

            identifier_text = "".join(identifier)
            is_simple_identifier = (
                bool(identifier_text)
                and (identifier_text[0].isalpha() or identifier_text[0] == "_")
                and all(
                    character.isalnum() or character in {"_", "$"}
                    for character in identifier_text
                )
            )
            if is_simple_identifier:
                tokens.append(identifier_text.casefold())
            else:
                tokens.append(f"{char}{identifier_text}{closing}")
            continue

        if char.isalpha() or char == "_":
            start = index
            index += 1
            while index < length and (
                sql[index].isalnum() or sql[index] in {"_", "$"}
            ):
                index += 1
            tokens.append(sql[start:index].casefold())
            continue

        if sql[index : index + 3] == "->>":
            tokens.append("->>")
            index += 3
            continue

        two_character_operator = sql[index : index + 2]
        if two_character_operator in {"<=", ">=", "<>", "!=", "==", "||", "->"}:
            tokens.append(two_character_operator)
            index += 2
            continue

        tokens.append(char)
        index += 1

    return tuple(tokens)


def _canonicalize_tokens(tokens: tuple[str, ...] | list[str]) -> str:
    return "\x1f".join(tokens)


def _canonicalize_sql_definition(sql: str) -> str:
    return _canonicalize_tokens(_sql_tokens(sql))


def _split_table_definition(
    tokens: tuple[str, ...],
) -> tuple[tuple[str, ...], list[list[str]], tuple[str, ...]]:
    """Split CREATE TABLE tokens into prefix, top-level clauses, and suffix."""

    try:
        body_start = tokens.index("(")
    except ValueError:
        return tokens, [], ()

    depth = 0
    body_end: int | None = None
    for position in range(body_start, len(tokens)):
        token = tokens[position]
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
            if depth == 0:
                body_end = position
                break

    if body_end is None:
        return tokens, [], ()

    clauses: list[list[str]] = []
    clause: list[str] = []
    depth = 0
    for token in tokens[body_start + 1 : body_end]:
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        if token == "," and depth == 0:
            clauses.append(clause)
            clause = []
        else:
            clause.append(token)
    clauses.append(clause)

    return tokens[:body_start], clauses, tokens[body_end + 1 :]


def _constraint_kind_before_conflict(tokens: list[str], position: int) -> str:
    preceding = tokens[:position]
    for index in range(len(preceding) - 1, -1, -1):
        token = preceding[index]
        if token == "unique":
            return "unique"
        if token == "check":
            return "check"
        if token == "null" and index > 0 and preceding[index - 1] == "not":
            return "not_null"
        if token == "key" and index > 0 and preceding[index - 1] == "primary":
            return "primary_key"
    return "other"


def _table_conflict_policies(sql: str) -> tuple[tuple[str, str], ...]:
    _prefix, clauses, _suffix = _split_table_definition(_sql_tokens(sql))
    policies: list[tuple[str, str]] = []
    accepted = {"rollback", "abort", "fail", "ignore", "replace"}

    for clause in clauses:
        for index in range(len(clause) - 2):
            if clause[index : index + 2] != ["on", "conflict"]:
                continue
            policy = clause[index + 2]
            if policy in accepted:
                policies.append((_constraint_kind_before_conflict(clause, index), policy))

    return tuple(sorted(policies))


def _remove_conflict_clause(tokens: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    accepted = {"rollback", "abort", "fail", "ignore", "replace"}
    while index < len(tokens):
        if (
            index + 2 < len(tokens)
            and tokens[index : index + 2] == ["on", "conflict"]
            and tokens[index + 2] in accepted
        ):
            index += 3
            continue
        result.append(tokens[index])
        index += 1
    return result


def _is_table_unique_clause(clause: list[str]) -> bool:
    if not clause:
        return False
    if clause[0] == "unique":
        return True
    return len(clause) >= 3 and clause[0] == "constraint" and clause[2] == "unique"


def _normalize_column_unique_constraints(clause: list[str]) -> list[str]:
    """Drop UNIQUE syntax represented semantically by SQLite unique indexes."""

    result: list[str] = []
    index = 0
    while index < len(clause):
        if clause[index] == "unique":
            index += 1
            continue
        if (
            index + 2 < len(clause)
            and clause[index] == "constraint"
            and clause[index + 2] == "unique"
        ):
            index += 3
            continue
        result.append(clause[index])
        index += 1
    return result


def _canonicalize_table_definition(sql: str) -> str:
    """Canonicalize table DDL while delegating UNIQUE semantics to PRAGMA indexes."""

    prefix, clauses, suffix = _split_table_definition(_sql_tokens(sql))
    if not clauses:
        return _canonicalize_sql_definition(sql)

    normalized_clauses: list[list[str]] = []
    for clause in clauses:
        if _is_table_unique_clause(clause):
            continue
        clause = _remove_conflict_clause(clause)
        clause = _normalize_column_unique_constraints(clause)
        normalized_clauses.append(clause)

    normalized: list[str] = [*prefix, "("]
    for index, clause in enumerate(normalized_clauses):
        if index:
            normalized.append(",")
        normalized.extend(clause)
    normalized.extend((")", *suffix))
    return _canonicalize_tokens(normalized)


def _index_predicate(sql: str | None) -> str | None:
    if sql is None:
        return None
    tokens = _sql_tokens(sql)
    depth = 0
    for index, token in enumerate(tokens):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif token == "where" and depth == 0:
            return _canonicalize_tokens(tokens[index + 1 :])
    return None


def _index_expression(sql: str | None, index_columns: tuple[tuple[object, ...], ...]) -> str | None:
    """Return raw index expression only when PRAGMA cannot name an indexed expression."""

    has_expression = any(
        len(column) >= 5 and column[0] == -2 and bool(column[4])
        for column in index_columns
    )
    if not has_expression or sql is None:
        return None

    tokens = _sql_tokens(sql)
    try:
        on_position = tokens.index("on")
        body_start = tokens.index("(", on_position + 1)
    except ValueError:
        return _canonicalize_sql_definition(sql)

    depth = 0
    expression_tokens: list[str] = []
    for token in tokens[body_start + 1 :]:
        if token == "(":
            depth += 1
        elif token == ")":
            if depth == 0:
                break
            depth -= 1
        expression_tokens.append(token)
    return _canonicalize_tokens(expression_tokens)


def _semantic_indexes(
    connection: sqlite3.Connection,
    quoted_table: str,
) -> tuple[_IndexSchema, ...]:
    indexes: list[_IndexSchema] = []
    for index_row in connection.execute(f"PRAGMA index_list({quoted_table})").fetchall():
        index_name = str(index_row[1])
        quoted_index = _quote_identifier(index_name)
        index_columns = tuple(
            tuple(row[1:])
            for row in connection.execute(f"PRAGMA index_xinfo({quoted_index})").fetchall()
        )
        sql_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            (index_name,),
        ).fetchone()
        index_sql = None if sql_row is None or sql_row[0] is None else str(sql_row[0])
        indexes.append(
            _IndexSchema(
                unique=bool(index_row[2]),
                partial=bool(index_row[4]),
                columns=index_columns,
                predicate=_index_predicate(index_sql),
                expression=_index_expression(index_sql, index_columns),
            )
        )

    # A UNIQUE index already supports the same lookup as an otherwise identical
    # non-unique index. Historical create_all adoption represents UNIQUE(name)
    # as one unique index, while fresh Alembic schema has a table UNIQUE plus a
    # redundant regular index. Treat those forms as semantically equivalent.
    unique_coverage = {
        (index.partial, index.columns, index.predicate, index.expression)
        for index in indexes
        if index.unique
    }
    normalized = [
        index
        for index in indexes
        if index.unique
        or (index.partial, index.columns, index.predicate, index.expression)
        not in unique_coverage
    ]
    return tuple(sorted(set(normalized), key=repr))


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
    table_rows = connection.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    tables: list[tuple[str, _TableSchema]] = []
    for table_name_value, table_sql_value in table_rows:
        table_name = str(table_name_value)
        table_sql = str(table_sql_value)
        quoted_table = _quote_identifier(table_name)
        columns = tuple(
            tuple(row[1:])
            for row in connection.execute(f"PRAGMA table_xinfo({quoted_table})").fetchall()
        )
        foreign_keys = tuple(
            tuple(row[2:])
            for row in connection.execute(
                f"PRAGMA foreign_key_list({quoted_table})"
            ).fetchall()
        )
        tables.append(
            (
                table_name,
                _TableSchema(
                    columns=columns,
                    foreign_keys=foreign_keys,
                    indexes=_semantic_indexes(connection, quoted_table),
                    definition=_canonicalize_table_definition(table_sql),
                    conflict_policies=_table_conflict_policies(table_sql),
                ),
            )
        )

    views_and_triggers = tuple(
        (
            str(object_type),
            str(name),
            str(table_name),
            _canonicalize_sql_definition(str(sql)),
        )
        for object_type, name, table_name, sql in connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE type IN ('view', 'trigger') AND sql IS NOT NULL
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
        with (
            _readonly_connection(source_path) as source,
            sqlite3.connect(target_path) as target,
        ):
            source.backup(target)
            target.commit()
    except sqlite3.DatabaseError as exc:
        raise DatabaseManagementError("SQLite backupの作成に失敗しました。") from exc


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
