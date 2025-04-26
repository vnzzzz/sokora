"""
メインページエンドポイント
----------------

トップページなど基本的なページ表示に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.attendance import attendance
from app.crud.location import location
from app.crud.user import user
from app.crud.group import group
from app.crud.user_type import user_type
from app.utils.date_utils import get_today_formatted
from app.utils.ui_utils import (
    generate_location_badges,
    has_data_for_day,
)

# ページ表示用ルーター
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def root_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """トップページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    today_str = get_today_formatted()

    # 今日の日付のデータを取得
    default_data = attendance.get_day_data(db, day=today_str)

    # 全ての勤務場所を取得
    locations = location.get_all_locations(db)

    # バッジを生成
    location_badges = generate_location_badges(locations)
    locations_badge_map = {loc["name"]: loc["badge"] for loc in location_badges}

    # データの有無を確認
    default_has_data = has_data_for_day(default_data)

    # グループ情報を取得
    groups = group.get_multi(db)
    groups_map = {g.group_id: g for g in groups}

    # ユーザータイプ情報を取得
    user_types = user_type.get_multi(db)
    user_types_map = {ut.user_type_id: ut for ut in user_types}

    # グループIDとグループ名のマッピングを作成
    group_id_to_name = {g.group_id: g.name for g in groups}
    # グループIDでソートするためのマッピング
    sorted_groups = sorted(groups, key=lambda g: int(g.group_id) if g.group_id is not None else 9999)
    sorted_group_names = [str(g.name) for g in sorted_groups]
    
    # ユーザー種別IDと名前のマッピングを作成
    user_type_id_to_name = {ut.user_type_id: ut.name for ut in user_types}
    # ユーザー種別をIDでソートするための準備
    user_type_id_mapping = {}

    # グループごとにユーザーを社員種別ごとに整理
    organized_by_group: Dict[str, Dict[str, Any]] = {}
    
    for location_name, users_list in default_data.items():
        # 勤務場所のバッジ情報を取得
        location_badge = locations_badge_map.get(location_name, "neutral")
        
        for user_data in users_list:
            # 必要なデータを追加
            user_data["location_name"] = location_name
            user_data["location_badge"] = location_badge
            
            # ユーザーの完全なオブジェクトを取得
            user_obj = user.get_by_user_id(db, user_id=user_data["user_id"])
            if not user_obj:
                continue
                
            # グループ情報を取得
            group_obj = None
            if user_obj.group_id in groups_map:
                group_obj = groups_map[user_obj.group_id]
            
            group_name = str(group_obj.name) if group_obj else "未分類"
            
            # 社員種別情報を取得
            user_type_name = "未分類"
            user_type_id = 9999  # 未分類の場合は大きな値を設定
            if user_obj.user_type_id in user_types_map:
                user_type_obj = user_types_map[user_obj.user_type_id]
                user_type_name = str(user_type_obj.name)
                user_type_id = int(user_type_obj.user_type_id)
                
                # ユーザー種別IDを記録
                user_type_id_mapping[user_type_name] = user_type_id
            
            # グループ構造を初期化
            if group_name not in organized_by_group:
                organized_by_group[group_name] = {
                    "user_types": set(),
                    "user_types_data": {},
                    "group_id": int(user_obj.group_id) if user_obj.group_id is not None else 9999  # 未分類は大きな値
                }
            
            # 社員種別を追加
            organized_by_group[group_name]["user_types"].add(user_type_name)
            
            # 社員種別ごとのリストを初期化
            if user_type_name not in organized_by_group[group_name]["user_types_data"]:
                organized_by_group[group_name]["user_types_data"][user_type_name] = []
            
            # ユーザーデータを追加
            organized_by_group[group_name]["user_types_data"][user_type_name].append(user_data)
    
    # グループをID順でソートするための準備
    sorted_organized_by_group = {}
    for group_name in sorted_group_names:
        if group_name in organized_by_group:
            sorted_organized_by_group[group_name] = organized_by_group[group_name]
    
    # 未分類グループがあれば最後に追加
    if "未分類" in organized_by_group:
        sorted_organized_by_group["未分類"] = organized_by_group["未分類"]
    
    # 社員種別をID順に並べ替え
    for group_data in sorted_organized_by_group.values():
        # 社員種別をID順にソート
        user_types_sorted = sorted(list(group_data["user_types"]), 
                                 key=lambda x: user_type_id_mapping.get(x, 9999))
        group_data["user_types"] = user_types_sorted
        
        # 各社員種別内でユーザーを名前順にソート
        for user_type_name in group_data["user_types"]:
            group_data["user_types_data"][user_type_name].sort(key=lambda u: u.get("user_name", ""))

    context = {
        "request": request,
        "default_day": today_str,
        "default_data": default_data,
        "default_locations": location_badges,
        "default_has_data": default_has_data,
        "organized_by_group": sorted_organized_by_group,
    }
    return templates.TemplateResponse("pages/index.html", context) 