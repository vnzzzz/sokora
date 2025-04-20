"""
sokoraAPI V1
==========

sokoraAPIエンドポイントのバージョン1です。
"""

# APIバージョン
__version__ = "0.1.0"

# モジュールのインポート
# ページ・UI関連
from . import pages
# データ操作API関連
from . import attendance, location, user

# APIルーターの設定
from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

# 各APIをマウント
api_router.include_router(user.router, prefix="/users")
api_router.include_router(attendance.router, prefix="/attendances")
api_router.include_router(location.router, prefix="/locations")
