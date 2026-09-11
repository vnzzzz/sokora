"""SQLite schemaのsemantic signature構築を担当する内部service module。"""

from __future__ import annotations

import sqlite3
from typing import NamedTuple


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
    conflict_policies: tuple[tuple[str, str, str], ...]


class _SchemaSignature(NamedTuple):
    tables: tuple[tuple[str, _TableSchema], ...]
    views_and_triggers: tuple[tuple[str, str, str, str], ...]


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sql_tokens(sql: str) -> tuple[str, ...]:
    """SQLite DDLをsemantic比較用tokenへ分解し、presentation差だけを正規化する。

    whitespaceと単純identifierのquote/case差は同一視する一方、string literal、operator、
    quoteしないと表現できないidentifierは区別したまま残す。後段のschema比較がSQL textの
    formatting差でrejectしないためのlexical normalizationで、constraint semantics自体は
    ここでは捨てない。
    """

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
            while index < length and (sql[index].isalnum() or sql[index] in {"_", "$"}):
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


def _constraint_identity_before_conflict(tokens: list[str], position: int) -> str:
    """Identify the exact constraint receiving an ON CONFLICT policy."""

    preceding = tokens[:position]
    identity_tokens: list[str] = []
    index = 0
    while index < len(preceding):
        if preceding[index] == "constraint" and index + 1 < len(preceding):
            # Constraint names are presentation metadata; the affected column(s)
            # and expression determine the behavior that must match.
            index += 2
            continue
        identity_tokens.append(preceding[index])
        index += 1
    return _canonicalize_tokens(identity_tokens)


def _table_conflict_policies(sql: str) -> tuple[tuple[str, str, str], ...]:
    _prefix, clauses, _suffix = _split_table_definition(_sql_tokens(sql))
    policies: list[tuple[str, str, str]] = []
    accepted = {"rollback", "abort", "fail", "ignore", "replace"}

    for clause in clauses:
        for index in range(len(clause) - 2):
            if clause[index : index + 2] != ["on", "conflict"]:
                continue
            policy = clause[index + 2]
            if policy in accepted:
                policies.append(
                    (
                        _constraint_kind_before_conflict(clause, index),
                        _constraint_identity_before_conflict(clause, index),
                        policy,
                    )
                )

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


def _strip_table_constraint_name(clause: list[str]) -> list[str]:
    if len(clause) >= 3 and clause[0] == "constraint":
        return clause[2:]
    return clause


def _is_table_constraint_clause(clause: list[str]) -> bool:
    normalized = _strip_table_constraint_name(clause)
    if not normalized:
        return False
    if normalized[0] in {"check", "foreign", "unique"}:
        return True
    return len(normalized) >= 2 and normalized[:2] == ["primary", "key"]


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
    """CREATE TABLE定義をsemantic schema比較向けにcanonicalizeする。

    column clauseの順序は保持する。table-level constraintは宣言順とconstraint名だけを
    presentation差として正規化し、CHECK/PRIMARY KEY/FOREIGN KEY等の内容は残す。UNIQUEは
    SQLiteが生成するindex signature側で比較するためDDL側から除き、ON CONFLICT policyは
    別signatureへ切り出してaffected constraintとpolicyを保持する。

    これによりAlembic生成DBとhistorical create_all adoptionの等価なschemaは同一視しつつ、
    constraint内容の実差分までは隠さない。
    """

    prefix, clauses, suffix = _split_table_definition(_sql_tokens(sql))
    if not clauses:
        return _canonicalize_sql_definition(sql)

    normalized_column_clauses: list[list[str]] = []
    normalized_table_constraints: list[list[str]] = []
    for clause in clauses:
        if _is_table_unique_clause(clause):
            continue
        clause = _remove_conflict_clause(clause)
        clause = _normalize_column_unique_constraints(clause)
        if _is_table_constraint_clause(clause):
            normalized_table_constraints.append(_strip_table_constraint_name(clause))
        else:
            normalized_column_clauses.append(clause)

    normalized_clauses = [
        *normalized_column_clauses,
        *sorted(normalized_table_constraints, key=_canonicalize_tokens),
    ]
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


def _index_expression(
    sql: str | None,
    index_columns: tuple[tuple[object, ...], ...],
) -> str | None:
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


def _semantic_foreign_keys(
    connection: sqlite3.Connection,
    quoted_table: str,
) -> tuple[tuple[object, ...], ...]:
    """SQLite-assigned FK IDやconstraint宣言順に依存しないFK signatureを返す。

    PRAGMAのconstraint IDはschema生成経路で変わり得るため同一視する。一方、composite FK内の
    column順、参照table/column、ON UPDATE、ON DELETE、MATCHはbehaviorへ影響するため保持する。
    constraint集合だけをsortし、複合keyのcolumn順までは並べ替えない。
    """

    rows = connection.execute(f"PRAGMA foreign_key_list({quoted_table})").fetchall()
    grouped: dict[int, list[tuple[object, ...]]] = {}
    for row in rows:
        grouped.setdefault(int(str(row[0])), []).append(tuple(row))

    constraints: list[tuple[object, ...]] = []
    for group_rows in grouped.values():
        ordered = sorted(group_rows, key=lambda row: int(str(row[1])))
        first = ordered[0]
        columns = tuple(
            (str(row[3]), None if row[4] is None else str(row[4])) for row in ordered
        )
        constraints.append(
            (
                str(first[2]),
                columns,
                str(first[5]),
                str(first[6]),
                str(first[7]),
            )
        )

    return tuple(sorted(constraints, key=repr))


def schema_signature(connection: sqlite3.Connection) -> _SchemaSignature:
    """restore互換性判定に必要なSQLite schemaのsemantic signatureを構築する。

    tableはcolumn metadata、FK、index、canonical DDL、constraint conflict policyを組み合わせる。
    view/triggerは実行behaviorを持つためcanonicalized full SQLを比較する。SQLite内部tableは
    application schemaではないので対象外とする。
    """
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
            for row in connection.execute(
                f"PRAGMA table_xinfo({quoted_table})"
            ).fetchall()
        )
        foreign_keys = _semantic_foreign_keys(connection, quoted_table)
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
