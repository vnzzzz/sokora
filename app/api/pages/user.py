"""
ユーザー管理ページエンドポイント
----------------

社員管理ページに関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.crud.user import user
from app.crud.group import group
from app.crud.user_type import user_type

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/user", response_class=HTMLResponse)
def user_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # 全てのユーザー基本情報 (名前, ID, 種別ID) を取得します。
    users_data = user.get_all_users(db)
    users = []

    # 完全なUserオブジェクトを含むリストを作成します。
    for user_name, user_id, user_type_id in users_data:
        user_obj = user.get_by_user_id(db, user_id=user_id)
        if user_obj:
            users.append((user_name, user_id, user_type_id, user_obj))

    # グループ情報をIDをキーとする辞書として取得します。
    groups = group.get_multi(db)
    groups_map = {g.group_id: g for g in groups}

    # ユーザータイプ情報をIDをキーとする辞書として取得します。
    user_types = user_type.get_multi(db)
    user_types_map = {ut.user_type_id: ut for ut in user_types}

    # 表示用にユーザーをグループ名でグルーピングします。
    grouped_users: Dict[str, List] = {}
    for user_name, user_id, user_type_id, user_obj in users:
        group_obj = groups_map.get(user_obj.group_id)
        group_name = str(group_obj.name) if group_obj else "未分類"

        if group_name not in grouped_users:
            grouped_users[group_name] = []

        grouped_users[group_name].append((user_name, user_id, user_type_id, user_obj))

    # 各グループ内のユーザーリストを社員種別IDでソートします。
    for g_name in list(grouped_users.keys()):
        grouped_users[g_name].sort(key=lambda u: u[2])

    # テンプレートに渡すコンテキストを作成します。
    return templates.TemplateResponse(
        "pages/user/index.html", {
            "request": request,
            "users": users, # Userオブジェクトを含むユーザーリスト
            "groups": groups, # 全グループのリスト
            "user_types": user_types, # 全社員種別のリスト
            "grouped_users": grouped_users, # グループ名で整理されたユーザー辞書
            "group_names": sorted(list(grouped_users.keys())) # ソートされたグループ名のリスト
        }
    ) 