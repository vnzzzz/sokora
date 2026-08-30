import asyncio
from typing import AsyncGenerator, Generator

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

# --- テスト用同期データベース設定 ---
# インメモリSQLiteの同期URL
TEST_DATABASE_URL = "sqlite:///:memory:"

# 同期エンジンを作成 (テスト用に StaticPool を使用)
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}, # SQLite用
    poolclass=StaticPool, # テストではコネクションを使い回さない
)

# 同期セッションファクトリ
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

# --- pytest-asyncio イベントループフィクスチャ (削除) ---
# @pytest.fixture(scope="session")
# def event_loop(request: pytest.FixtureRequest) -> Generator:
#     """pytest-asyncio 用のイベントループフィクスチャ (非推奨)"""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()

# --- テスト用データベースセットアップフィクスチャ ---
@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None, None, None]:
    """テストセッション開始時にDBテーブルを作成し、終了時に破棄する"""
    Base.metadata.create_all(bind=engine) # 同期エンジンを使用
    yield
    Base.metadata.drop_all(bind=engine) # 同期エンジンを使用

# --- FastAPIアプリケーションと依存性オーバーライド ---

# get_db をオーバーライドする 同期 関数
def override_get_db() -> Generator[Session, None, None]: # 戻り値を Session に
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# @pytest_asyncio.fixture(scope="function") # 非同期セッションを使わないため不要
# async def db() -> AsyncGenerator[AsyncSession, None]:
#     """テストごとに独立した非同期DBセッションを提供するフィクスチャ"""
#     async with TestingSessionLocal() as session:
#         yield session
#         await session.rollback() # 各テスト後にロールバック

# test_app フィクスチャは async_client で必要なので残すが、内部で使う override_get_db は同期
@pytest.fixture(scope="function")
def test_app() -> Generator[FastAPI, None, None]:
    """依存関係をオーバーライドしたテスト用FastAPIアプリケーションインスタンス"""
    main_app.dependency_overrides[get_db] = override_get_db
    yield main_app # yield に変更して後処理でクリア
    main_app.dependency_overrides.clear() # テスト後にオーバーライドをクリア

# --- 非同期テストクライアント ---

@pytest_asyncio.fixture(scope="function")
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """テスト用の非同期HTTPクライアント"""
    # ASGITransport を使用するように修正
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client 