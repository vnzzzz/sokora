import time
from typing import Any, AsyncGenerator, Generator, List

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base, DatabaseRuntime, get_db
from app.main import app as main_app


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """テスト関数ごとにインメモリDBとセッションを作成・提供するフィクスチャ"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Base.metadataからtableを作る前に全modelを登録する。
    from app.models import (  # noqa: F401
        Attendance,
        CustomHoliday,
        Group,
        Location,
        User,
        UserType,
    )

    Base.metadata.create_all(bind=engine)

    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        Base.metadata.drop_all(bind=engine)
        db_session.close()


@pytest.fixture(scope="function")
def test_data_tracker(db: Session) -> Generator[dict, None, None]:
    """テスト内で作成されたデータを追跡し、自動クリーンアップするフィクスチャ"""
    created_objects: dict[str, List[Any]] = {
        "groups": [],
        "user_types": [],
        "locations": [],
        "users": [],
        "attendances": [],
    }

    test_timestamp = int(time.time())

    def create_test_name(base_name: str) -> str:
        """テスト専用のユニークな名前を生成"""
        return f"テスト_{base_name}_{test_timestamp}_{len(created_objects['groups']) + len(created_objects['user_types']) + len(created_objects['locations'])}"

    def register_created_object(object_type: str, obj: Any) -> None:
        """作成したオブジェクトを追跡リストに登録"""
        if object_type in created_objects:
            created_objects[object_type].append(obj)

    tracker = {
        "created_objects": created_objects,
        "create_test_name": create_test_name,
        "register_created_object": register_created_object,
        "test_timestamp": test_timestamp,
    }

    try:
        yield tracker
    finally:
        try:
            # FK依存を壊さないようchild rowから削除する。
            for att in created_objects["attendances"]:
                try:
                    db.delete(att)
                except Exception as e:
                    print(f"Failed to delete attendance {att.id}: {e}")

            for user in created_objects["users"]:
                try:
                    db.delete(user)
                except Exception as e:
                    print(f"Failed to delete user {user.id}: {e}")

            for location in created_objects["locations"]:
                try:
                    db.delete(location)
                except Exception as e:
                    print(f"Failed to delete location {location.id}: {e}")

            for user_type in created_objects["user_types"]:
                try:
                    db.delete(user_type)
                except Exception as e:
                    print(f"Failed to delete user_type {user_type.id}: {e}")

            for group in created_objects["groups"]:
                try:
                    db.delete(group)
                except Exception as e:
                    print(f"Failed to delete group {group.id}: {e}")

            db.commit()
        except Exception as e:
            print(f"Error during test data cleanup: {e}")
            db.rollback()


@pytest.fixture(scope="function")
def db_with_data(db: Session, test_data_tracker: dict) -> Session:
    """基本テストデータが投入されたDBセッション"""
    from app.crud.group import group as crud_group
    from app.crud.location import location as crud_location
    from app.crud.user_type import user_type as crud_user_type
    from app.schemas.group import GroupCreate
    from app.schemas.location import LocationCreate
    from app.schemas.user_type import UserTypeCreate

    # 複数testが名称で参照するためseed名を固定する。
    group_data = GroupCreate(name="Test Group")
    test_group = crud_group.create(db, obj_in=group_data)
    test_data_tracker["register_created_object"]("groups", test_group)

    user_type_data = UserTypeCreate(name="Test Type")
    test_user_type = crud_user_type.create(db, obj_in=user_type_data)
    test_data_tracker["register_created_object"]("user_types", test_user_type)

    location_data = LocationCreate(name="Test Location")
    test_location = crud_location.create(db, obj_in=location_data)
    test_data_tracker["register_created_object"]("locations", test_location)

    db.commit()
    return db


@pytest.fixture(scope="function")
def test_app(
    db: Session,
) -> Generator[FastAPI, None, None]:
    """依存関係とapplication-owned DB runtimeを同じテストDBへbindする。"""
    # request dependencyとmanaged sessionが同じfixture DBを観測するようruntimeも差し替える。
    engine = db.get_bind()
    assert isinstance(engine, Engine)
    test_runtime = DatabaseRuntime(
        database_url="sqlite:///:memory:",
        engine=engine,
        session_factory=sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        ),
    )
    previous_runtime = getattr(main_app.state, "database_runtime", None)
    main_app.state.database_runtime = test_runtime
    main_app.dependency_overrides[get_db] = lambda: db
    try:
        yield main_app
    finally:
        main_app.dependency_overrides.clear()
        main_app.state.database_runtime = previous_runtime


@pytest_asyncio.fixture(scope="function")
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """テスト用の非同期HTTPクライアント"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
