"""
sokora - 勤怠管理アプリケーション
===========================

このパッケージにはsokora勤怠管理アプリケーションのソースコードが含まれています。
FastAPIで構築されたシンプルな勤怠記録ツールです。

機能:
- 日次の勤怠状況表示
- 月間カレンダービュー
- ユーザーごとのデータ閲覧
- ユーザー、勤怠種別、グループ管理
- CSVによるデータエクスポート

技術スタック:
- FastAPI (バックエンド)
- HTMX, Alpine.js (フロントエンド)
- SQLAlchemy (ORM)
- SQLite (データベース)
- Jinja2 (テンプレート)
"""

from .core.config import APP_VERSION, logger

__version__ = APP_VERSION
__all__ = ["__version__", "logger"]
__author__ = "Sokora Team"
