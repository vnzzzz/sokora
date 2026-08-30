from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 - register model metadata for Alembic autogenerate
from app.core.settings import AppSettings
from app.db.session import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# DATABASE_URL is the database connection source of truth for both the app and
# migration commands. ConfigParser uses percent interpolation, so literal
# percent signs in SQLAlchemy URLs must be escaped when stored in Alembic config.
database_url = AppSettings.from_env().database_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
