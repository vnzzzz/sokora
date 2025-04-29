"""
ユーザー管理ページエンドポイント
----------------

社員管理ページに関連するルートハンドラー
"""

from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.group import group
from app.crud.user import user
from app.crud.user_type import user_type
from app.db.session import get_db
from app import schemas, services # スキーマとサービスをインポート
from app.models.user import User # User モデルをインポート

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
        user_obj = user.get(db, id=user_id)
        if user_obj:
            users.append((user_name, user_id, user_type_id, user_obj))

    # グループ情報をIDをキーとする辞書として取得します。
    groups = group.get_multi(db)
    groups_map = {g.id: g for g in groups}

    # ユーザータイプ情報をIDをキーとする辞書として取得します。
    user_types = user_type.get_multi(db)
    user_types_map = {ut.id: ut for ut in user_types}

    # 表示用にユーザーをグループ名でグルーピングします。
    grouped_users: Dict[str, List[Tuple[str, str, int, User]]] = {}
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


@router.get("/pages/user/edit/{user_id}", response_class=HTMLResponse)
def get_user_edit_form(request: Request, user_id: str, db: Session = Depends(get_db)) -> Any:
    """指定されたユーザーの編集フォームをHTMLフラグメントとして返します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: ユーザーID
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    # 関連情報を含めてユーザーを取得 (見つからなければ404)
    user_data = user.get_user_with_details(db, id=user_id)
    if not user_data:
        # ここで404を返す代わりに、エラーメッセージを含むHTMLを返すことも検討できるが、
        # 一般的にはリソースが存在しない場合は 404 が適切
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")

    groups = group.get_multi(db, limit=1000) # 十分な数を取得
    user_types = user_type.get_multi(db, limit=1000) # 十分な数を取得

    return templates.TemplateResponse(
        "components/user/_user_edit_form.html",
        {
            "request": request,
            "user": user_data,
            "groups": groups,
            "user_types": user_types,
        }
    )


@router.post("/pages/user/row", response_class=HTMLResponse)
def handle_create_user_row(
    request: Request,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate = Depends(schemas.UserCreate.as_form)
) -> Any:
    """新規ユーザーを作成し、新しいテーブル行のHTMLフラグメントを返します。

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション
        user_in: 新規ユーザーの入力データ

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    try:
        created_user = services.user_service.create_user_with_validation(db=db, user_in=user_in)
        # 作成成功時は、新しい行を描画して返す (関連情報も取得)
        user_row_data = user.get_user_with_details(db, id=str(created_user.id))
        if not user_row_data: # 基本的に作成直後なので存在するはずだが念のため
            raise HTTPException(status_code=500, detail="Failed to retrieve created user details")
            
        return templates.TemplateResponse(
            "components/user/_user_row.html",
            {"request": request, "user": user_row_data}
        )
    except HTTPException as e:
        # バリデーションエラー等の場合、エラーメッセージを含むフォームエラー部分を返す
        response = templates.TemplateResponse(
            "components/common/_form_error.html",
            {"request": request, "error_message": e.detail}
        )
        response.status_code = e.status_code # エラーに応じたステータスコードを設定
        # HTMXがエラーメッセージを正しい場所に挿入するようにHX-Retargetヘッダーを追加
        response.headers["HX-Retarget"] = "#add-form-error" # 追加フォームのエラー表示領域ID
        return response


@router.put("/pages/user/row/{user_id}", response_class=HTMLResponse)
def handle_update_user_row(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    user_in: schemas.UserUpdate = Depends(schemas.UserUpdate.as_form)
) -> Any:
    """ユーザー情報を更新し、更新されたテーブル行のHTMLフラグメントを返します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: ユーザーID
        db: データベースセッション
        user_in: 更新されたユーザーの入力データ

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    try:
        updated_user = services.user_service.update_user_with_validation(
            db=db, user_id=user_id, user_in=user_in
        )
        # 更新成功時は、更新された行を描画して返す (関連情報も取得)
        user_row_data = user.get_user_with_details(db, id=str(updated_user.id))
        if not user_row_data: # 基本的に更新直後なので存在するはずだが念のため
            raise HTTPException(status_code=500, detail="Failed to retrieve updated user details")

        return templates.TemplateResponse(
            "components/user/_user_row.html",
            {"request": request, "user": user_row_data}
        )
    except HTTPException as e:
        # バリデーションエラー等の場合、エラーメッセージを含むフォームエラー部分を返す
        response = templates.TemplateResponse(
            "components/common/_form_error.html",
            {"request": request, "error_message": e.detail}
        )
        response.status_code = e.status_code
        # HX-Retargetヘッダーを追加（編集フォームのエラー表示領域ID）
        response.headers["HX-Retarget"] = f"#edit-form-error-{user_id}"
        return response 