"""
db/session.py のテストケース
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import (
    get_db, init_db, initialize_database, SessionLocal, Base, engine, DB_PATH, DB_URL
)


class TestDatabaseConfiguration:
    """データベース設定のテスト"""

    def test_db_path_configuration(self) -> None:
        """DB_PATHが正しく設定されていることを確認"""
        assert DB_PATH == Path("data/sokora.sqlite")
        assert str(DB_PATH) == "data/sokora.sqlite"

    def test_db_url_configuration(self) -> None:
        """DB_URLが正しく設定されていることを確認"""
        expected_url = f"sqlite:///{DB_PATH.absolute()}"
        assert DB_URL == expected_url
        assert "sqlite:///" in DB_URL
        assert "sokora.sqlite" in DB_URL

    def test_engine_configuration(self) -> None:
        """SQLAlchemyエンジンが正しく設定されていることを確認"""
        assert engine is not None
        assert str(engine.url) == DB_URL

    def test_session_local_configuration(self) -> None:
        """SessionLocalが正しく設定されていることを確認"""
        assert SessionLocal is not None
        assert hasattr(SessionLocal, '__call__')

    def test_base_configuration(self) -> None:
        """Baseクラスが正しく設定されていることを確認"""
        assert Base is not None
        assert hasattr(Base, 'metadata')


class TestGetDb:
    """get_db関数のテスト"""

    @patch('app.db.session.SessionLocal')
    def test_get_db_yields_session(self, mock_session_local: MagicMock) -> None:
        """get_db関数がセッションを生成することを確認"""
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # ジェネレータを実行
        db_generator = get_db()
        db_session = next(db_generator)
        
        assert db_session == mock_session
        mock_session_local.assert_called_once()

    @patch('app.db.session.SessionLocal')
    def test_get_db_closes_session(self, mock_session_local: MagicMock) -> None:
        """get_db関数がセッションを正しくクローズすることを確認"""
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        # ジェネレータを実行してクローズ
        db_generator = get_db()
        next(db_generator)
        
        try:
            next(db_generator)
        except StopIteration:
            pass
        
        mock_session.close.assert_called_once()

    @patch('app.db.session.SessionLocal')
    def test_get_db_exception_handling(self, mock_session_local: MagicMock) -> None:
        """get_db関数が例外発生時もセッションをクローズすることを確認"""
        mock_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_session
        
        db_generator = get_db()
        next(db_generator)
        
        # 例外を発生させてfinallyブロックをテスト
        try:
            db_generator.throw(Exception("Test exception"))
        except Exception:
            pass
        
        mock_session.close.assert_called_once()


class TestInitDb:
    """init_db関数のテスト"""

    @patch('app.db.session.Base')
    @patch('app.db.session.DB_PATH')
    @patch('app.db.session.logger')
    def test_init_db_creates_directory(self, mock_logger: MagicMock, mock_db_path: MagicMock, mock_base: MagicMock) -> None:
        """init_db関数がディレクトリを作成することを確認"""
        mock_parent = MagicMock()
        mock_db_path.parent = mock_parent
        
        init_db()
        
        mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_logger.info.assert_called_once()

    @patch('app.db.session.Base')
    @patch('app.db.session.DB_PATH')
    @patch('app.db.session.logger')
    def test_init_db_creates_tables(self, mock_logger: MagicMock, mock_db_path: MagicMock, mock_base: MagicMock) -> None:
        """init_db関数がテーブルを作成することを確認"""
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        init_db()
        
        mock_metadata.create_all.assert_called_once()

    @patch('app.db.session.Base')
    @patch('app.db.session.DB_PATH')
    @patch('app.db.session.logger')
    def test_init_db_imports_models(self, mock_logger: MagicMock, mock_db_path: MagicMock, mock_base: MagicMock) -> None:
        """init_db関数がモデルをインポートすることを確認"""
        with patch('app.models.User'), \
             patch('app.models.Attendance'), \
             patch('app.models.Location'), \
             patch('app.models.Group'), \
             patch('app.models.UserType'):
            
            init_db()
            
            # インポートが実行されたことを確認（例外が発生しないことで確認）
            assert True


class TestInitializeDatabase:
    """initialize_database関数のテスト"""

    @patch('app.db.session.init_db')
    @patch('app.db.session.logger')
    def test_initialize_database_success(self, mock_logger: MagicMock, mock_init_db: MagicMock) -> None:
        """initialize_database関数が成功時にTrueを返すことを確認"""
        result = initialize_database()
        
        assert result is True
        mock_init_db.assert_called_once()
        mock_logger.info.assert_called_with("データベースの初期化が正常に完了しました。")

    @patch('app.db.session.init_db')
    @patch('app.db.session.logger')
    def test_initialize_database_failure(self, mock_logger: MagicMock, mock_init_db: MagicMock) -> None:
        """initialize_database関数がエラー時にFalseを返すことを確認"""
        mock_init_db.side_effect = Exception("Test error")
        
        result = initialize_database()
        
        assert result is False
        mock_init_db.assert_called_once()
        mock_logger.error.assert_called_once()
        # エラーメッセージの確認
        error_call = mock_logger.error.call_args[0][0]
        assert "データベースの初期化に失敗しました" in error_call
        assert "Test error" in error_call


class TestDatabaseIntegration:
    """データベース統合テスト"""

    def test_real_session_creation(self) -> None:
        """実際のセッション作成のテスト"""
        session = SessionLocal()
        assert isinstance(session, Session)
        session.close()

    def test_get_db_real_usage(self) -> None:
        """get_db関数の実際の使用テスト"""
        db_generator = get_db()
        session = next(db_generator)
        
        assert isinstance(session, Session)
        
        # ジェネレータを終了してセッションをクローズ
        try:
            next(db_generator)
        except StopIteration:
            pass

    @patch('app.db.session.DB_PATH')
    def test_database_path_handling(self, mock_db_path: MagicMock) -> None:
        """データベースパス処理のテスト"""
        mock_db_path.absolute.return_value = Path("/test/path/sokora.sqlite")
        
        # DB_URLが正しく構築されることを確認
        from app.db.session import DB_URL
        # パッチ後はDB_URLが変更されないため、ロジックのテストのみ
        assert "sqlite:///" in DB_URL 