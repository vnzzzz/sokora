"""
ページエンドポイント
----------------

HTMLページ表示に関連するルートハンドラーをまとめたパッケージ
"""

from fastapi import APIRouter

from app.routers.pages.analysis import router as analysis_router
from app.routers.pages.attendance import router as attendance_router
from app.routers.pages.calendar import router as calendar_router
from app.routers.pages.csv import router as csv_router
from app.routers.pages.group import router as group_router
from app.routers.pages.location import router as location_router
from app.routers.pages.register import router as register_router
from app.routers.pages.top import router as top_router
from app.routers.pages.user import router as user_router
from app.routers.pages.user_type import router as user_type_router

# メインルーター
router = APIRouter()

# 各モジュールのルーターをインクルード
router.include_router(top_router)
router.include_router(user_router)
router.include_router(attendance_router)
router.include_router(calendar_router)
router.include_router(location_router)
router.include_router(group_router)
router.include_router(user_type_router)
router.include_router(csv_router) 
router.include_router(register_router)
router.include_router(analysis_router)