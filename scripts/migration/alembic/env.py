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

LEGACY_HEAD_REVISION = "6b8f3dbe1e1a"
LEGACY_HEAD_COLUMNS = {
    "groups": {"id", "name", "order"},
    "user_types": {"id", "name", "order"},
    "locations": {"id", "name", "category", "order"},
    "users": {"id", "username", "group_id", "user_type_id"},
    "attendance": {"id", "user_id", "date", "location_id", "note"},
    "custom_holidays": {"id", "date", "name", "created_at", "updated_at"},
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


def _is_legacy_head_schema(inspector: Inspector) -> bool:
    """Return whether an unversioned DB matches the pre-#54 current schema."""
    application_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if application_tables != set(LEGACY_HEAD_COLUMNS):
        return False

    for table_name, expected_columns in LEGACY_HEAD_COLUMNS.items():
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if actual_columns != expected_columns:
            return False
    return True


def _adopt_legacy_history_if_needed(connection: Connection) -> None:
    """Place pristine/current unversioned DBs at the immutable legacy head.

    The historical migration chain starts with ALTER TABLE operations and cannot
    create a pristine database. Existing ``create_all`` databases, meanwhile,
    already contain the legacy-head schema but have no Alembic version marker.
    Only those two unambiguous states skip the immutable legacy revisions. Older
    unversioned schemas continue through the historical migration chain normally.
    """
    migration_context = MigrationContext.configure(connection)
    if migration_context.get_current_revision() is not None:
        return

    inspector = inspect(connection)
    application_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if application_tables and not _is_legacy_head_schema(inspector):
        return

    script = ScriptDirectory.from_config(config)
    migration_context.stamp(script, LEGACY_HEAD_REVISION)


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
