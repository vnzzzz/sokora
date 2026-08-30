"""Database engine and session lifecycle helpers."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import logger
from app.core.settings import AppSettings

Base = declarative_base()


@dataclass
class DatabaseRuntime:
    """Engine and session factory bound to one database URL."""

    database_url: str
    engine: Engine
    session_factory: sessionmaker[Session]

    def dispose(self) -> None:
        self.engine.dispose()


def create_database_runtime(database_url: str) -> DatabaseRuntime:
    """Create an isolated database runtime for a database URL."""
    url = make_url(database_url)
    engine_kwargs: dict[str, object] = {}
    if url.get_backend_name() == "sqlite":
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_kwargs)
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    return DatabaseRuntime(
        database_url=database_url,
        engine=engine,
        session_factory=session_factory,
    )


@lru_cache(maxsize=None)
def _cached_database_runtime(database_url: str) -> DatabaseRuntime:
    return create_database_runtime(database_url)


def get_default_database_runtime() -> DatabaseRuntime:
    """Return the lazily-created runtime for the current process settings."""
    settings = AppSettings.from_env()
    return _cached_database_runtime(settings.database_url)


def clear_database_runtime_cache() -> None:
    """Dispose cached default runtimes; primarily useful for test isolation."""
    for runtime in _cached_database_runtime.cache_info() and []:
        runtime.dispose()
    _cached_database_runtime.cache_clear()


def SessionLocal() -> Session:
    """Compatibility session constructor using the current DATABASE_URL."""
    return get_default_database_runtime().session_factory()


def get_app_database_runtime(request: Request) -> DatabaseRuntime:
    """Return the database runtime associated with the current FastAPI app."""
    runtime = getattr(request.app.state, "database_runtime", None)
    if isinstance(runtime, DatabaseRuntime):
        return runtime

    settings = request.app.state.settings
    runtime = create_database_runtime(settings.database_url)
    request.app.state.database_runtime = runtime
    return runtime


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session."""
    runtime = get_app_database_runtime(request)
    db = runtime.session_factory()
    try:
        yield db
    finally:
        db.close()


def sqlite_database_path(database_url: str) -> Path | None:
    """Resolve a file-backed SQLite URL to a filesystem path."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    if url.database == ":memory:":
        return None

    path = Path(url.database)
    return path if path.is_absolute() else Path.cwd() / path


def seed_database(
    runtime: DatabaseRuntime,
    days_back: int = 60,
    days_forward: int = 60,
) -> Dict[str, int]:
    """Seed a newly-created local SQLite database."""
    from scripts.seeding.data_seeder import run_seeder

    return run_seeder(
        days_back=days_back,
        days_forward=days_forward,
        skip_init=True,
        session_factory=runtime.session_factory,
    )


def init_db(runtime: DatabaseRuntime | None = None) -> None:
    """Create the current schema using the supplied database runtime.

    This remains the pre-Alembic compatibility path until issue #54 replaces
    ``create_all`` with migrations for both fresh and existing databases.
    """
    runtime = runtime or get_default_database_runtime()
    database_path = sqlite_database_path(runtime.database_url)
    if database_path is not None:
        database_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database schema: %s", runtime.database_url)
    Base.metadata.create_all(bind=runtime.engine)


def initialize_database(runtime: DatabaseRuntime | None = None) -> bool:
    """Initialize schema and seed a fresh file-backed SQLite database."""
    runtime = runtime or get_default_database_runtime()
    database_path = sqlite_database_path(runtime.database_url)
    db_missing = database_path is not None and not database_path.exists()

    try:
        init_db(runtime)
        if db_missing:
            logger.info("Database file is missing; seeding initial data")
            seed_result = seed_database(runtime, days_back=60, days_forward=60)
            logger.info("Database seeding completed: %s", seed_result)
        logger.info("Database initialization completed")
        return True
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc, exc_info=True)
        return False
