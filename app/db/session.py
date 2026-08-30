"""Database engine and session lifecycle helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Generator
from urllib.parse import unquote, urlsplit

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.applications import Starlette

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


def _sqlite_uri_enabled(url: URL) -> bool:
    return str(url.query.get("uri", "")).lower() == "true"


def _sqlite_is_memory_database(url: URL) -> bool:
    if url.database in {None, "", ":memory:"}:
        return True
    if not _sqlite_uri_enabled(url):
        return False
    return (
        url.database == "file::memory:"
        or str(url.query.get("mode", "")).lower() == "memory"
    )


def create_database_runtime(database_url: str) -> DatabaseRuntime:
    """Create an isolated database runtime for a database URL."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        engine_kwargs: dict[str, object] = {
            "connect_args": {"check_same_thread": False}
        }
        if _sqlite_is_memory_database(url):
            engine_kwargs["poolclass"] = StaticPool
        engine = create_engine(database_url, **engine_kwargs)
    else:
        engine = create_engine(database_url)

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


_default_database_runtimes: dict[str, DatabaseRuntime] = {}


def get_default_database_runtime() -> DatabaseRuntime:
    """Return the lazily-created runtime for the current process settings."""
    database_url = AppSettings.from_env().database_url
    runtime = _default_database_runtimes.get(database_url)
    if runtime is None:
        runtime = create_database_runtime(database_url)
        _default_database_runtimes[database_url] = runtime
    return runtime


def clear_database_runtime_cache() -> None:
    """Dispose cached default runtimes; primarily useful for test isolation."""
    for runtime in _default_database_runtimes.values():
        runtime.dispose()
    _default_database_runtimes.clear()


def SessionLocal() -> Session:
    """Compatibility session constructor using the current DATABASE_URL."""
    return get_default_database_runtime().session_factory()


def get_app_database_runtime(app: Starlette) -> DatabaseRuntime:
    """Return the database runtime associated with one application instance."""
    runtime = getattr(app.state, "database_runtime", None)
    if isinstance(runtime, DatabaseRuntime):
        return runtime

    settings: AppSettings = app.state.settings_provider()
    runtime = create_database_runtime(settings.database_url)
    app.state.database_runtime = runtime
    return runtime


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session."""
    runtime = get_app_database_runtime(request.app)
    db = runtime.session_factory()
    try:
        yield db
    finally:
        db.close()


def sqlite_database_path(database_url: str) -> Path | None:
    """Resolve a file-backed SQLite URL to the filesystem path SQLite opens."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    if _sqlite_is_memory_database(url):
        return None

    database = url.database
    if _sqlite_uri_enabled(url) and database.startswith("file:"):
        parsed = urlsplit(database)
        if parsed.netloc and parsed.netloc != "localhost":
            database = f"//{parsed.netloc}{parsed.path}"
        else:
            database = parsed.path
        database = unquote(database)

    path = Path(database)
    return path if path.is_absolute() else Path.cwd() / path


def seed_database(
    runtime: DatabaseRuntime,
    days_back: int = 60,
    days_forward: int = 60,
) -> Dict[str, int]:
    """Seed a newly-created local SQLite database using the supplied runtime."""
    from scripts.seeding.data_seeder import bootstrap_core_data, seed_attendance

    db = runtime.session_factory()
    try:
        bootstrap_result = bootstrap_core_data(db)
        attendances = seed_attendance(
            db,
            days_back=days_back,
            days_forward=days_forward,
        )
        return {
            **bootstrap_result,
            "attendances": len(attendances),
        }
    finally:
        db.close()


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
