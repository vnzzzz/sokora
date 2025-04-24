"""
ページエンドポイント
----------------

HTMLページ表示に関連するルートハンドラーをまとめたパッケージ
"""

from fastapi import APIRouter

from app.api.pages.main import router as main_router
from app.api.pages.user import router as user_router
from app.api.pages.attendance import router as attendance_router
from app.api.pages.calendar import router as calendar_router
from app.api.pages.location import router as location_router
from app.api.pages.group import router as group_router
from app.api.pages.user_type import router as user_type_router
from app.api.pages.csv import router as csv_router

# メインルーター
router = APIRouter()

# 各モジュールのルーターをインクルード
router.include_router(main_router)
router.include_router(user_router)
router.include_router(attendance_router)
router.include_router(calendar_router)
router.include_router(location_router)
router.include_router(group_router)
router.include_router(user_type_router)
router.include_router(csv_router) 