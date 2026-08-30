from logging.config import fileConfig

from alembic import context
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, inspect, pool
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

import app.models  # noqa: F401 - register model metadata for Alembic autogenerate
from app.core.settings import AppSettings
from app.db.session import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

PRE_CUSTOM_HOLIDAYS_REVISION = "bdbed9dbd6c9"
LEGACY_HEAD_REVISION = "6b8f3dbe1e1a"
LEGACY_HEAD_COLUMNS = {
    "groups": {"id", "name", "order"},
    "user_types": {"id", "name", "order"},
    "locations": {"id", "name", "category", "order"},
    "users": {"id", "username", "group_id", "user_type_id"},
    "attendance": {"id", "user_id", "date", "location_id", "note"},
    "custom_holidays": {"id", "date", "name", "created_at", "updated_at"},
}
PRE_CUSTOM_HOLIDAYS_COLUMNS = {
    table_name: columns
    for table_name, columns in LEGACY_HEAD_COLUMNS.items()
    if table_name != "custom_holidays"
}

# DATABASE_URL is the database connection source of truth for both the app and
# migration commands. Programmatic callers can provide the application runtime's
# exact URL so in-memory SQLite migrations use the same connection-backed DB.
database_url = (
    config.attributes.get("database_url") or AppSettings.from_env().database_url
)
# ConfigParser uses percent interpolation, so literal percent signs in SQLAlchemy
# URLs must be escaped when stored in Alembic config.
config.set_main_option("sqlalchemy.url", str(database_url).replace("%", "%%"))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _matches_schema(inspector: Inspector, expected_columns: dict[str, set[str]]) -> bool:
    application_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if application_tables != set(expected_columns):
        return False

    for table_name, expected_table_columns in expected_columns.items():
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if actual_columns != expected_table_columns:
            return False
    return True


def _legacy_revision_for_unversioned_schema(inspector: Inspector) -> str | None:
    """Resolve unambiguous historical create_all snapshots to Alembic revisions."""
    application_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if not application_tables:
        # The immutable historical chain cannot create a pristine database, so
        # skip it and let the #54 baseline create the current schema.
        return LEGACY_HEAD_REVISION

    if _matches_schema(inspector, LEGACY_HEAD_COLUMNS):
        return LEGACY_HEAD_REVISION

    # c678232-era application code already had the first four historical schema
    # changes in its SQLAlchemy models, but custom_holidays had not been added.
    # Replaying from revision zero would therefore try to add existing columns.
    if _matches_schema(inspector, PRE_CUSTOM_HOLIDAYS_COLUMNS):
        return PRE_CUSTOM_HOLIDAYS_REVISION

    # Older base-compatible schemas should traverse the immutable migration chain.
    # Unknown mixed states are deliberately not guessed at here.
    return None


def _adopt_legacy_history_if_needed(connection: Connection) -> None:
    """Adopt known unversioned DB snapshots at their matching legacy revision."""
    migration_context = MigrationContext.configure(connection)
    if migration_context.get_current_revision() is not None:
        return

    inspector = inspect(connection)
    revision = _legacy_revision_for_unversioned_schema(inspector)
    if revision is None:
        return

    script = ScriptDirectory.from_config(config)
    migration_context.stamp(script, revision)


def _run_migrations(connection: Connection) -> None:
    _adopt_legacy_history_if_needed(connection)
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    external_connection = config.attributes.get("connection")
    if isinstance(external_connection, Connection):
        _run_migrations(external_connection)
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # An outer transaction is required because legacy adoption stamps the
    # version table before Alembic configures its migration transaction. It also
    # makes programmatic and CLI migration behavior consistent on SQLite.
    with connectable.begin() as connection:
        _run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
