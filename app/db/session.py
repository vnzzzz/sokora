"""
データベースセッション管理
========================

データベース接続とセッション管理のための機能を提供します。
SQLAlchemyを使用したデータベース操作の基盤となるモジュールです。
"""

import os
from pathlib import Path
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from ..core.config import logger

# SQLiteデータベースファイルのパスとURL設定
DB_PATH = Path("data/sokora.sqlite")
DB_URL = f"sqlite:///{DB_PATH.absolute()}"

# SQLAlchemyエンジンを作成（SQLiteの同時接続に対応）
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# セッション生成用のファクトリを設定
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデル定義のベースクラスを作成
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    依存性注入用のデータベースセッションを提供するジェネレータ

    FastAPIのDependsで使用され、リクエスト毎に新しいセッションを生成し、
    リクエスト完了時に確実にセッションをクローズします。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    データベースを初期化してテーブルを作成します

    モデル定義に基づいてデータベーススキーマを構築し、
    必要なディレクトリ構造を確保します。
    """
    # モデルのインポートを遅延させて循環参照を防ぐ
    from ..models import User, Attendance, Location

    # データ用ディレクトリの存在確認と作成
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # モデル定義に基づくテーブル作成
    logger.info(f"Initializing database at {DB_PATH}")
    Base.metadata.create_all(bind=engine)


def initialize_database() -> bool:
    """
    アプリケーション起動時のデータベース初期化処理を実行します

    データベースの初期化を安全に行い、失敗時にはエラーログを記録します。

    Returns:
        bool: 初期化処理の成功・失敗
    """
    try:
        # データベース初期化を実行
        init_db()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False
