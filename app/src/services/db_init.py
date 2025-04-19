"""
Database initialization service
===========================

Service for initializing database and importing initial data.
"""

from sqlalchemy.orm import Session

from ..db.session import SessionLocal, init_db
from ..core.config import logger


def initialize_database():
    """
    データベースを初期化し、必要なテーブルを作成する

    Returns:
        bool: 成功したかどうか
    """
    try:
        # データベースの初期化
        init_db()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False
