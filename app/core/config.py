"""
アプリケーション設定
==============

環境変数からアプリケーション設定を読み込み管理します。
"""

import os
import logging
from datetime import datetime

# アプリケーションバージョン
APP_VERSION = "1.0.0"

# ログレベル設定（環境変数から取得、デフォルトはINFO）
log_level = os.environ.get("SOKORA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ルートロガーの取得
logger = logging.getLogger("sokora")
