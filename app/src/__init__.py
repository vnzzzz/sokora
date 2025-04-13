"""
Sokora - 勤務管理アプリケーション
================================

このパッケージはSokora勤務管理アプリケーションのソースコードを含みます。
FastAPIを使用したシンプルな勤務状況管理ツールです。

機能:
- 日別の勤務状況表示
- 月別カレンダー表示
- ユーザー別データ閲覧
- CSVデータのインポート/エクスポート
"""

import logging
import os

# アプリケーションのバージョン
__version__ = "0.1.0"

# ログレベルの設定（環境変数から取得するか、デフォルトでINFOを使用）
log_level = os.environ.get("SOKORA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# ルートロガーの取得
logger = logging.getLogger("sokora")
