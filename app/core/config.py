"""
アプリケーション設定
==============

環境変数からアプリケーション設定を読み込み管理します。
"""

import os
import logging
from datetime import datetime

# アプリケーション全体のバージョン情報
APP_VERSION = "1.0.0"

# ロギング設定
# 環境変数 `SOKORA_LOG_LEVEL` からログレベルを取得します (デフォルトは INFO)。
# ログフォーマットと日付フォーマットも設定します。
log_level = os.environ.get("SOKORA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO), # 無効なレベル指定時はINFOにフォールバック
    format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# アプリケーション全体で使用するルートロガーを取得します。
logger = logging.getLogger("sokora")
