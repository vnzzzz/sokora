"""
Database Session Management
========================

Database connection and session management functions.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..core.config import logger

# データベースファイルのパスを設定
DB_PATH = Path("data/sokora.sqlite")
DB_URL = f"sqlite:///{DB_PATH.absolute()}"

# エンジンを作成
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# セッションファクトリを作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """データベースセッションを取得するヘルパー関数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """データベースの初期化と必要なテーブルの作成"""
    from ..models import User, Attendance, Location
    from .base_class import Base

    # DBディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # テーブルを作成（存在していなければ）
    logger.info(f"Initializing database at {DB_PATH}")
    Base.metadata.create_all(bind=engine)
