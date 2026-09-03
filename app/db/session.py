"""Database engine、request session、migrationのprocess-local lifecycleを管理する。

DB backend固有のengine設定とapplication instanceごとのresource ownershipをこのmoduleへ
集約する。特にSQLite restoreでは、request sessionのdrain、engine再生成、fail-closed fencingを
同じDatabaseRuntimeが調停し、置換中のDBへ新しいrequestが接続しないことを保証する。
"""

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Condition
from typing import Any, Dict
from urllib.parse import unquote, urlsplit

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.applications import Starlette

from app.core.config import logger
from app.core.settings import AppSettings

Base = declarative_base()

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_CONFIG_PATH = _REPOSITORY_ROOT / "scripts" / "migration" / "alembic.ini"
_ALEMBIC_SCRIPT_PATH = _REPOSITORY_ROOT / "scripts" / "migration" / "alembic"


class DatabaseRuntimeUnavailableError(RuntimeError):
    """fail-closedへfenceされたDB runtimeへの新規session要求を表す。

    restore recovery等でDB stateを安全と確認できなくなった後は、callerが同じprocessで
    接続を再試行してreject済みDBへ戻ることを許可しない。process restart/manual recoveryが
    完了するまで、このexceptionをrequest boundaryへ伝播させる。
    """


@dataclass
class DatabaseRuntime:
    """1つのdatabase URLに対するengine/session factoryと排他状態を所有する。

    通常requestは`managed_session()`を通してactive session数へ参加する。DB file replacement等
    のmaintenanceは`exclusive_maintenance()`で新規sessionを止め、既存sessionがcloseするまで
    drainしてからengineを切り替える。

    unrecoverable failureでは`mark_unavailable()`でruntimeをfenceする。fenceはmaintenance解除と
    別概念であり、一度設定したprocessは新規DB sessionを再開しない。
    """

    database_url: str
    engine: Engine
    session_factory: sessionmaker[Session]
    _condition: Condition = field(default_factory=Condition, init=False, repr=False)
    _active_sessions: int = field(default=0, init=False, repr=False)
    _maintenance_active: bool = field(default=False, init=False, repr=False)
    _unavailable_reason: str | None = field(default=None, init=False, repr=False)

    @contextmanager
    def managed_session(self) -> Iterator[Session]:
        """request用Sessionを生成し、そのlifetimeをmaintenance drainへ登録する。

        maintenance中の新規requestは完了まで待機する。runtimeがfenceされた場合はsessionを
        作らず`DatabaseRuntimeUnavailableError`を返す。Session生成または`close()`が失敗しても
        active counterは必ず減算し、maintenance waiterを永久待機させない。
        """
        with self._condition:
            while self._maintenance_active and self._unavailable_reason is None:
                self._condition.wait()
            if self._unavailable_reason is not None:
                raise DatabaseRuntimeUnavailableError(self._unavailable_reason)
            factory = self.session_factory
            self._active_sessions += 1

        try:
            db = factory()
        except Exception:
            with self._condition:
                self._active_sessions -= 1
                if self._active_sessions == 0:
                    self._condition.notify_all()
            raise

        try:
            yield db
        finally:
            try:
                db.close()
            finally:
                with self._condition:
                    self._active_sessions -= 1
                    if self._active_sessions == 0:
                        self._condition.notify_all()

    @contextmanager
    def exclusive_maintenance(self) -> Iterator[None]:
        """新規request sessionを停止し、既存sessionをdrainして排他maintenanceを行う。

        複数maintenance callerは直列化される。context内ではactive request sessionが0であり、
        engine/file replacementとrecoveryをrequest trafficから隔離できる。終了時は通常requestを
        再開するが、context内でruntimeがfenceされた場合は`managed_session()`が引き続き拒否する。
        """
        with self._condition:
            if self._unavailable_reason is not None:
                raise DatabaseRuntimeUnavailableError(self._unavailable_reason)
            while self._maintenance_active:
                self._condition.wait()
                if self._unavailable_reason is not None:
                    raise DatabaseRuntimeUnavailableError(self._unavailable_reason)
            self._maintenance_active = True
            while self._active_sessions:
                self._condition.wait()

        try:
            yield
        finally:
            with self._condition:
                self._maintenance_active = False
                self._condition.notify_all()

    def mark_unavailable(self, reason: str) -> None:
        """unrecoverable DB failure後、このprocessからの新規DB接続をfail-closedで停止する。

        `reason`はoperator log/error用の内部診断値であり、health response等のpublic contractへ
        そのまま公開しない。wait中のrequest/maintenance callerを起こし、fenceを即時観測させる。
        """
        with self._condition:
            self._unavailable_reason = reason
            self._condition.notify_all()

    @property
    def unavailable_reason(self) -> str | None:
        """runtimeがfenceされている場合だけ内部diagnostic reasonを返す。"""
        with self._condition:
            return self._unavailable_reason

    def recreate_connections(self) -> None:
        """現在のpoolを破棄し、同じdatabase URLへengine/session factoryを再bindする。

        SQLite DB fileのatomic replacement後など、既存connectionが旧fileを参照し得る場合に使う。
        callerは通常`exclusive_maintenance()`内で呼び、requestが旧/new poolを跨がないようにする。
        """
        self.engine.dispose()
        engine, session_factory = _create_engine_and_session_factory(self.database_url)
        self.engine = engine
        self.session_factory = session_factory

    def dispose(self) -> None:
        """このruntimeが所有するSQLAlchemy connection poolを解放する。"""
        self.engine.dispose()


def sqlalchemy_database_url(database_url: str) -> URL:
    """application contractのDB URLをproduction driver向けSQLAlchemy URLへ正規化する。

    bare PostgreSQL URLはportableなapplication contractだが、SQLAlchemyのbare
    ``postgresql://`` dialectはhistorically psycopg2を選ぶ。sokoraはPsycopg 3を同梱するため、
    driver未指定のPostgreSQL URLだけ`postgresql+psycopg`へ変換する。明示driverは保持する。
    """
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


def _database_url_for_logging(database_url: str) -> str:
    """credentialとquery parameterを除いたDB URLをdiagnostic log用に返す。"""
    url = sqlalchemy_database_url(database_url)
    return url.set(query={}).render_as_string(hide_password=True)


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


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    """SQLiteの全DB-API connectionでforeign key enforcementを有効化する。"""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _create_engine_and_session_factory(
    database_url: str,
) -> tuple[Engine, sessionmaker[Session]]:
    url = sqlalchemy_database_url(database_url)
    if url.get_backend_name() == "sqlite":
        engine_kwargs: dict[str, object] = {
            "connect_args": {"check_same_thread": False}
        }
        if _sqlite_is_memory_database(url):
            engine_kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **engine_kwargs)
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    else:
        engine = create_engine(url)

    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    return engine, session_factory


def create_database_runtime(database_url: str) -> DatabaseRuntime:
    """指定database URL専用のengine/session resourcesを持つDatabaseRuntimeを作成する。"""
    engine, session_factory = _create_engine_and_session_factory(database_url)
    return DatabaseRuntime(
        database_url=database_url,
        engine=engine,
        session_factory=session_factory,
    )


_default_database_runtimes: dict[str, DatabaseRuntime] = {}


def get_default_database_runtime() -> DatabaseRuntime:
    """process環境の`DATABASE_URL`ごとにlazy cacheされたdefault runtimeを返す。

    application instanceでは`get_app_database_runtime()`を優先する。このdefault cacheはCLIや
    compatibility caller向けで、異なるURLを同じruntimeへ誤って再bindしない。
    """
    database_url = AppSettings.from_env().database_url
    runtime = _default_database_runtimes.get(database_url)
    if runtime is None:
        runtime = create_database_runtime(database_url)
        _default_database_runtimes[database_url] = runtime
    return runtime


def clear_database_runtime_cache() -> None:
    """default runtime cacheをdisposeして空にし、主にtest間のprocess stateを分離する。"""
    for runtime in _default_database_runtimes.values():
        runtime.dispose()
    _default_database_runtimes.clear()


def SessionLocal() -> Session:
    """current `DATABASE_URL`のdefault runtimeからSessionを作るcompatibility constructor。"""
    return get_default_database_runtime().session_factory()


def get_app_database_runtime(app: Starlette) -> DatabaseRuntime:
    """1 application instanceが所有するDatabaseRuntimeをlazyに取得・作成する。

    runtimeをmodule-global singletonにせず`app.state`へbindすることで、test/application instance間の
    DB resourceを分離する。同じapplication内のrequestは同じruntimeを共有し、maintenance/fenceを
    一貫して観測する。
    """
    runtime = getattr(app.state, "database_runtime", None)
    if isinstance(runtime, DatabaseRuntime):
        return runtime

    settings: AppSettings = app.state.settings_provider()
    runtime = create_database_runtime(settings.database_url)
    app.state.database_runtime = runtime
    return runtime


def get_db(request: Request) -> Generator[Session, None, None]:
    """requestをapplication DatabaseRuntimeのsession lifecycleへ参加させるFastAPI dependency。

    direct `session_factory()`ではなく`managed_session()`を使うため、DB maintenanceは既存requestの
    closeを待ち、新規requestを安全にblock/fenceできる。
    """
    runtime = get_app_database_runtime(request.app)
    with runtime.managed_session() as db:
        yield db


def sqlite_database_path(database_url: str) -> Path | None:
    """file-backed SQLite URLが実際に開くfilesystem pathを返す。

    PostgreSQLとin-memory SQLiteはfile操作の対象ではないためNoneを返す。relative pathはprocessの
    current working directory基準でabsolute化し、backup/restoreがSQLAlchemy URL表現を独自解釈
    しないための共通resolverとして利用する。
    """
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


def alembic_heads() -> tuple[str, ...]:
    """current source treeがrestore candidateに要求するAlembic head revisionを返す。"""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(_ALEMBIC_CONFIG_PATH))
    config.set_main_option("script_location", str(_ALEMBIC_SCRIPT_PATH))
    return tuple(ScriptDirectory.from_config(config).get_heads())


def migrate_database(runtime: DatabaseRuntime | None = None) -> None:
    """指定runtimeのschemaをcurrent Alembic headまでupgradeする。

    Alembicへapplication runtimeと同じconnectionを渡す。特にin-memory SQLiteはconnectionごとに
    別DBになり得るため、別engineでmigrationするとrequest側のschemaが更新されない。

    failureはcallerへ伝播し、startup側が未更新schemaでserviceを開始しないようにする。
    """
    from alembic import command
    from alembic.config import Config

    runtime = runtime or get_default_database_runtime()
    database_path = sqlite_database_path(runtime.database_url)
    if database_path is not None:
        database_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Migrating database schema: %s", _database_url_for_logging(runtime.database_url)
    )
    config = Config(str(_ALEMBIC_CONFIG_PATH))
    config.set_main_option("script_location", str(_ALEMBIC_SCRIPT_PATH))
    config.attributes["database_url"] = runtime.database_url

    with runtime.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def init_db(runtime: DatabaseRuntime | None = None) -> None:
    """legacy caller向けschema setup aliasとしてAlembic migrationへ委譲する。"""
    migrate_database(runtime)


def seed_database(
    runtime: DatabaseRuntime,
    days_back: int = 60,
    days_forward: int = 60,
) -> Dict[str, int]:
    """fresh local SQLite向けの初期master/attendance dataを指定runtimeへ投入する。

    startup側がfresh file-backed SQLiteと判定した場合だけ呼ぶ。PostgreSQLや既存DBを暗黙に
    seedしないため、backend/新規性の判断はこのfunctionでは行わない。
    """
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


def initialize_database(runtime: DatabaseRuntime | None = None) -> bool:
    """startup前提となるschema migrationとfresh SQLite seedを完了する。

    すべてのbackendでAlembic headまでmigrationする。seedするのはstartup開始時にDB fileが
    存在しなかったfile-backed SQLiteだけで、PostgreSQL/in-memory SQLite/既存SQLiteには
    自動seedしない。

    migrationまたはseed failureは再送出する。callerはこのfunctionが成功しない限りrequestを
    受け付けず、partial initializationをhealthy runtimeとして扱わない。
    """
    runtime = runtime or get_default_database_runtime()
    database_path = sqlite_database_path(runtime.database_url)
    db_missing = database_path is not None and not database_path.exists()

    try:
        migrate_database(runtime)
        if db_missing:
            logger.info("Database file is missing; seeding initial data")
            seed_result = seed_database(runtime, days_back=60, days_forward=60)
            logger.info("Database seeding completed: %s", seed_result)
        logger.info("Database initialization completed")
        return True
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc, exc_info=True)
        raise
