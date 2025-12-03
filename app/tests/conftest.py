import asyncio
from typing import AsyncGenerator, Generator, List, Any
import time

import pytest
import pytest_asyncio
from fastapi import FastAPI
# ASGITransport をインポート
from httpx import AsyncClient, ASGITransport
# 同期エンジン作成用の create_engine と StaticPool をインポート
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session # Session をインポート
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # 不要

# --- アプリケーションとDB設定のインポート ---
from app.db.session import Base, get_db # get_db と Base をインポート
from app.main import app as main_app
# トップレベルでモデルをインポート
# from app.models import User, Attendance, Location, Group, UserType

# --- テスト用データベースフィクスチャ ---
@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """テスト関数ごとにインメモリDBとセッションを作成・提供するフィクスチャ"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # TestingSessionLocal の定義を関数内に移動し、インデントを修正
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # モデルをインポート (インデントを修正)
    from app.models import User, Attendance, Location, Group, UserType, CustomHoliday  # noqa: F401
    Base.metadata.create_all(bind=engine) # テーブル作成

    db_session = TestingSessionLocal()
    try:
        yield db_session # テスト関数にセッションを提供
    finally:
        Base.metadata.drop_all(bind=engine) # テーブル削除
        db_session.close()


@pytest.fixture(scope="function")
def test_data_tracker(db: Session) -> Generator[dict, None, None]:
    """テスト内で作成されたデータを追跡し、自動クリーンアップするフィクスチャ"""
    created_objects: dict[str, List[Any]] = {
        'groups': [],
        'user_types': [],
        'locations': [],
        'users': [],
        'attendances': []
    }
    
    # テスト用のタイムスタンプを生成
    test_timestamp = int(time.time())
    
    def create_test_name(base_name: str) -> str:
        """テスト専用のユニークな名前を生成"""
        return f"テスト_{base_name}_{test_timestamp}_{len(created_objects['groups']) + len(created_objects['user_types']) + len(created_objects['locations'])}"
    
    def register_created_object(object_type: str, obj: Any) -> None:
        """作成したオブジェクトを追跡リストに登録"""
        if object_type in created_objects:
            created_objects[object_type].append(obj)
    
    # ヘルパー関数を辞書に追加
    tracker = {
        'created_objects': created_objects,
        'create_test_name': create_test_name,
        'register_created_object': register_created_object,
        'test_timestamp': test_timestamp
    }
    
    try:
        yield tracker
    finally:
        # テスト終了時にすべての作成されたオブジェクトを削除
        try:
            # 外部キー制約の順序を考慮して削除
            # attendances -> users -> locations/user_types/groups の順序
            for att in created_objects['attendances']:
                try:
                    db.delete(att)
                except Exception as e:
                    print(f"Failed to delete attendance {att.id}: {e}")
            
            for user in created_objects['users']:
                try:
                    db.delete(user)
                except Exception as e:
                    print(f"Failed to delete user {user.id}: {e}")
            
            for location in created_objects['locations']:
                try:
                    db.delete(location)
                except Exception as e:
                    print(f"Failed to delete location {location.id}: {e}")
            
            for user_type in created_objects['user_types']:
                try:
                    db.delete(user_type)
                except Exception as e:
                    print(f"Failed to delete user_type {user_type.id}: {e}")
            
            for group in created_objects['groups']:
                try:
                    db.delete(group)
                except Exception as e:
                    print(f"Failed to delete group {group.id}: {e}")
            
            db.commit()
        except Exception as e:
            print(f"Error during test data cleanup: {e}")
            db.rollback()


# --- データ作成済みのテスト用DBフィクスチャ ---
@pytest.fixture(scope="function")
def db_with_data(db: Session, test_data_tracker: dict) -> Session:
    """基本テストデータが投入されたDBセッション"""
    from app.schemas.group import GroupCreate
    from app.schemas.user_type import UserTypeCreate
    from app.schemas.location import LocationCreate
    from app.crud.group import group as crud_group
    from app.crud.user_type import user_type as crud_user_type
    from app.crud.location import location as crud_location
    
    # テスト用グループを作成
    group_data = GroupCreate(name=test_data_tracker['create_test_name']("Group"))
    test_group = crud_group.create(db, obj_in=group_data)
    test_data_tracker['register_created_object']('groups', test_group)
    
    # テスト用ユーザータイプを作成
    user_type_data = UserTypeCreate(name=test_data_tracker['create_test_name']("Type"))
    test_user_type = crud_user_type.create(db, obj_in=user_type_data)
    test_data_tracker['register_created_object']('user_types', test_user_type)
    
    # テスト用ロケーションを作成
    location_data = LocationCreate(name=test_data_tracker['create_test_name']("Location"))
    test_location = crud_location.create(db, obj_in=location_data)
    test_data_tracker['register_created_object']('locations', test_location)
    
    db.commit()
    return db


# --- FastAPIアプリケーションと依存性オーバーライド ---

# get_db をオーバーライドする関数 (dbフィクスチャに依存)
# def override_get_db(db_session: Session = Depends(db)) -> Generator[Session, None, None]:
#     yield db_session

# test_app フィクスチャ (dbフィクスチャに依存)
@pytest.fixture(scope="function")
def test_app(db: Session) -> Generator[FastAPI, None, None]: # db フィクスチャを引数で受け取る
    """依存関係をオーバーライドしたテスト用FastAPIアプリケーションインスタンス"""
    # override_get_db を使わず、dbフィクスチャのセッションを直接返すようにlambdaで上書き
    main_app.dependency_overrides[get_db] = lambda: db 
    yield main_app
    main_app.dependency_overrides.clear()

# --- 非同期テストクライアント (変更なし、test_app に依存) ---
@pytest_asyncio.fixture(scope="function")
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """テスト用の非同期HTTPクライアント"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client 
