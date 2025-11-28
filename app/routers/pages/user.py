"""
ユーザー管理ページエンドポイント
----------------

社員管理ページに関連するルートハンドラー
"""

from typing import Any, Dict, List, Tuple, Optional
import json

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import asc, nullslast

from app.crud.group import group
from app.crud.user import user
from app.crud.user_type import user_type
from app.db.session import get_db
from app import schemas # スキーマをインポート
from app.services import user_service # user_service を直接インポート
from app.models.user import User # User モデルをインポート

# ルーター定義
router = APIRouter(prefix="/ui/users", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
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
    # グループのorder情報を保存する辞書
    group_orders: Dict[str, float] = {}
    
    for user_name, user_id, user_type_id, user_obj in users:
        group_obj = groups_map.get(user_obj.group_id)
        group_name = str(group_obj.name) if group_obj else "未分類"

        if group_name not in grouped_users:
            grouped_users[group_name] = []
            # グループのorder情報を保存（未分類は最後に表示）
            if group_obj:
                group_orders[group_name] = float(group_obj.order) if group_obj.order is not None else float('inf')
            else:
                group_orders[group_name] = float('inf')

        grouped_users[group_name].append((user_name, user_id, user_type_id, user_obj))

    # 各グループ内のユーザーリストを社員種別IDでソートします。
    for g_name in list(grouped_users.keys()):
        grouped_users[g_name].sort(key=lambda u: u[2])

    # グループ名をorder順にソート（orderがNoneの場合は最後に表示）
    sorted_group_names = sorted(grouped_users.keys(), key=lambda g: group_orders.get(g, float('inf')))

    # テンプレートに渡すコンテキストを作成します。
    return templates.TemplateResponse(
        "pages/user.html", {
            "request": request,
            "users": users, # Userオブジェクトを含むユーザーリスト
            "groups": groups, # 全グループのリスト
            "user_types": user_types, # 全社員種別のリスト
            "grouped_users": grouped_users, # グループ名で整理されたユーザー辞書
            "group_names": sorted_group_names # order順でソートされたグループ名のリスト
        }
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{user_id}", response_class=HTMLResponse)
async def user_modal(
    request: Request,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Any:
    """社員の追加または編集モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 編集する場合の社員ID (None の場合は新規追加)
        db: データベースセッション

    Returns:
        HTMLResponse: モーダルHTMLフラグメント
    """
    user_obj = None
    if user_id:
        user_obj = user.get(db, id=user_id)
        if not user_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")
    
    # グループと社員種別の一覧を取得
    groups = group.get_multi(db)
    user_types = user_type.get_multi(db)
    
    modal_id = f"user-modal-{user_id or 'new'}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "user": user_obj,
        "groups": groups,
        "user_types": user_types,
        "modal_id": modal_id,
        "errors": {}
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "components/partials/users/user_modal.html", ctx, headers=headers
    )


@router.get("/delete-modal/{user_id}", response_class=HTMLResponse)
async def user_delete_modal(request: Request, user_id: str, db: Session = Depends(get_db)) -> Any:
    """社員の削除確認モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 削除する社員ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除確認モーダルHTMLフラグメント
    """
    user_obj = user.get(db, id=user_id)
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")
    
    modal_id = f"user-delete-modal-{user_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "user": user_obj,
        "modal_id": modal_id,
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "components/partials/users/user_delete_modal.html", ctx, headers=headers
    )


@router.post("", response_class=HTMLResponse)
async def create_user(
    request: Request,
    user_in: schemas.UserCreate = Depends(schemas.UserCreate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """新規社員を作成します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_in: 社員作成スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = "user-modal-new"
    
    try:
        # 社員作成を試みる
        created_user = user_service.create_user_with_validation(db=db, user_in=user_in)
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "components/partials/users/user_modal.html",
            {
                "request": request,
                "user": created_user,
                "groups": group.get_multi(db),
                "user_types": user_type.get_multi(db),
                "modal_id": modal_id
            },
            headers={
                "HX-Trigger": json.dumps({
                    "closeModal": modal_id,
                    "refreshPage": True,
                    "showMessage": f"社員 {created_user.username} を追加しました。"
                })
            }
        )
    except HTTPException as e:
        # エラー時は同じモーダルを表示し、エラーメッセージを表示
        errors = {"error": [e.detail]}
        
        # フィールド別エラー
        if e.status_code == 422 and hasattr(e, 'detail') and isinstance(e.detail, list):
            errors = {}
            for err in e.detail:
                if 'loc' in err and len(err['loc']) > 1:
                    field = err['loc'][1]
                    if field not in errors:
                        errors[field] = []
                    errors[field].append(err['msg'])
        
        print(f"Create user error: {errors}")
        
        return templates.TemplateResponse(
            "components/partials/users/user_modal.html",
            {
                "request": request, 
                "user": None,
                "groups": group.get_multi(db),
                "user_types": user_type.get_multi(db),
                "modal_id": modal_id,
                "errors": errors
            },
            status_code=200  # エラー時でもHTMXにはステータス200で返す
        )


@router.put("/{user_id}", response_class=HTMLResponse)
async def update_user(
    request: Request,
    user_id: str,
    user_in: schemas.UserUpdate = Depends(schemas.UserUpdate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """社員を更新します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 更新する社員ID
        user_in: 社員更新スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = f"user-modal-{user_id}"
    
    try:
        # 社員更新を試みる
        updated_user = user_service.update_user_with_validation(
            db=db, user_id=user_id, user_in=user_in
        )
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "components/partials/users/user_modal.html",
            {
                "request": request,
                "user": updated_user,
                "groups": group.get_multi(db),
                "user_types": user_type.get_multi(db),
                "modal_id": modal_id
            },
            headers={
                "HX-Trigger": json.dumps({
                    "closeModal": modal_id,
                    "refreshPage": True,
                    "showMessage": f"社員 {updated_user.username} を更新しました。"
                })
            }
        )
    except HTTPException as e:
        # エラー時は同じモーダルを表示し、エラーメッセージを表示
        return templates.TemplateResponse(
            "components/partials/users/user_modal.html",
            {
                "request": request, 
                "user": user.get(db, id=user_id),
                "groups": group.get_multi(db),
                "user_types": user_type.get_multi(db),
                "modal_id": modal_id,
                "errors": {"username": [e.detail]}
            }
        )


@router.delete("/{user_id}", response_class=HTMLResponse)
async def delete_user(request: Request, user_id: str, db: Session = Depends(get_db)) -> Any:
    """社員を削除します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 削除する社員ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除完了後のレスポンス
    """
    try:
        # 社員が存在するか確認
        user_obj = user.get(db, id=user_id)
        if not user_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found")
        
        # 社員の削除処理
        user.remove(db=db, id=user_id)
        
        # モーダルを閉じて画面をリロードするトリガーを返す
        modal_id = f"user-delete-modal-{user_id}"
        return HTMLResponse(
            content="",
            status_code=200,
            headers={
                "HX-Trigger": json.dumps({
                    "closeModal": modal_id,
                    "refreshPage": True,
                    "showMessage": f"社員 {user_obj.username} を削除しました。"
                })
            }
        )
    except HTTPException as e:
        # エラー時は同じモーダルを表示し、エラーメッセージを表示
        modal_id = f"user-delete-modal-{user_id}"
        ctx = {
            "request": request,
            "user": user.get(db, id=user_id),
            "modal_id": modal_id,
            "warning_message": e.detail
        }
        return templates.TemplateResponse(
            "components/partials/users/user_delete_modal.html", ctx
        )



@router.post("/rows", response_class=HTMLResponse)
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
        created_user = user_service.create_user_with_validation(db=db, user_in=user_in)
        # 作成成功時は、新しい行を描画して返す (関連情報も取得)
        user_row_data = user.get_user_with_details(db, id=str(created_user.id))
        if not user_row_data: # 基本的に作成直後なので存在するはずだが念のため
            raise HTTPException(status_code=500, detail="Failed to retrieve created user details")
            
        response = templates.TemplateResponse(
            "components/user/_user_row.html",
            {"request": request, "user": user_row_data}
        )
        # 変更: 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"ユーザー {created_user.username} を追加しました。", 
            "refreshPage": True
        })
        return response
    except HTTPException as e:
        # バリデーションエラー等の場合、エラーメッセージを含むフォームエラー部分を返す
        response = templates.TemplateResponse(
            "components/common/_form_error.html",
            {"request": request, "error_message": e.detail}
        )
        response.status_code = e.status_code
        response.headers["HX-Retarget"] = "#add-form-error" # 追加フォームのエラー表示領域ID
        # エラー時にもメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({"showMessage": e.detail, "isError": True})
        return response


@router.put("/rows/{user_id}", response_class=HTMLResponse)
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
        updated_user = user_service.update_user_with_validation(
            db=db, user_id=user_id, user_in=user_in
        )
        # 更新成功時は、更新された行を描画して返す (関連情報も取得)
        user_row_data = user.get_user_with_details(db, id=str(updated_user.id))
        if not user_row_data: # 基本的に更新直後なので存在するはずだが念のため
            raise HTTPException(status_code=500, detail="Failed to retrieve updated user details")

        response = templates.TemplateResponse(
            "components/user/_user_row.html",
            {"request": request, "user": user_row_data}
        )
        # 変更: 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"ユーザー {updated_user.username} を更新しました。", 
            "refreshPage": True
        })
        return response
    except HTTPException as e:
        # バリデーションエラー等の場合、エラーメッセージを含むフォームエラー部分を返す
        response = templates.TemplateResponse(
            "components/common/_form_error.html",
            {"request": request, "error_message": e.detail}
        )
        response.status_code = e.status_code
        response.headers["HX-Retarget"] = f"#edit-form-error-{user_id}"
        # エラー時にもメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({"showMessage": e.detail, "isError": True})
        return response 
