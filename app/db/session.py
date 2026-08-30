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
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.core.config import logger

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
    データベースセッションを取得するための依存性注入（DI）用関数。

    FastAPIの `Depends` と共に使用され、リクエストごとに独立したセッションを提供し、
    リクエスト処理完了後にセッションを自動的にクローズします。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    データベーススキーマを初期化（テーブル作成）します。

    SQLAlchemyモデル定義に基づいて、データベース内にテーブルを作成します。
    データベースファイルが格納されるディレクトリが存在しない場合は作成します。
    """
    # モデル定義をインポートします。
    # (関数内でインポートすることで、モジュール読み込み時の循環参照を回避)
    from app.models import User, Attendance, Location, Group, UserType

    # データベースファイルが格納される`data/`ディレクトリを作成します (存在しない場合)。
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # モデル定義に基づいてデータベーステーブルを作成します。
    logger.info(f"データベースを初期化しています: {DB_PATH}")
    Base.metadata.create_all(bind=engine)


def initialize_database() -> bool:
    """
    アプリケーション起動時に呼び出されるデータベース初期化関数。

    `init_db` を呼び出し、データベースの初期化を実行します。
    成功時はTrue、エラー発生時はFalseを返します。
    """
    try:
        init_db()
        logger.info("データベースの初期化が正常に完了しました。")
        return True
    except Exception as e:
        logger.error(f"データベースの初期化に失敗しました: {str(e)}", exc_info=True)
        return False
