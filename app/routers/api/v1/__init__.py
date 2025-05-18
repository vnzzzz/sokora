"""
Sokora API V1
==========

Sokora APIエンドポイントのバージョン1です。
すべてのルーターをまとめて、APIマウントポイントを管理します。
"""

# APIバージョン
__version__ = "0.1.0"

from fastapi import APIRouter

# データ操作API関連
from app.routers.api.v1 import attendance, csv, group, location, user, user_type

# メインAPIルーターの作成（すべてのAPIエンドポイントを統合）
api_router = APIRouter(prefix="/api")

# 各APIをマウント
# ユーザー関連API
api_router.include_router(
    user.router, 
    prefix="/users", 
    tags=["Users"]
)

# 勤怠データ関連API
api_router.include_router(
    attendance.router, 
    prefix="/attendances", 
    tags=["Attendance"]
)

# 勤怠種別関連API
api_router.include_router(
    location.router, 
    prefix="/locations", 
    tags=["Locations"]
)

# グループ関連API
api_router.include_router(
    group.router, 
    prefix="/groups", 
    tags=["Groups"]
)

# 社員種別関連API
api_router.include_router(
    user_type.router, 
    prefix="/user_types", 
    tags=["UserTypes"]
)

# CSVデータダウンロードAPI
api_router.include_router(
    csv.router,
    tags=["Data"]
)

# v1 APIルーター
router = api_router
