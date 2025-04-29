import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends
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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # モデルをインポート
    from app.models import User, Attendance, Location, Group, UserType
    Base.metadata.create_all(bind=engine) # テーブル作成

    db_session = TestingSessionLocal()
    try:
        yield db_session # テスト関数にセッションを提供
    finally:
        Base.metadata.drop_all(bind=engine) # テーブル削除
        db_session.close()

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