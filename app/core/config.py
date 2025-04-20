"""
アプリケーション設定
==============

環境変数からアプリケーション設定を読み込み管理します。
"""

import os
import logging

# アプリケーションバージョン
APP_VERSION = "1.0.0"

# ログレベル設定（環境変数から取得、デフォルトはINFO）
log_level = os.environ.get("SOKORA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# ルートロガーの取得
logger = logging.getLogger("sokora")
