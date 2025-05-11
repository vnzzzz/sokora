"""
社員種別管理ページエンドポイント
----------------

社員種別の設定管理に関連するルートハンドラー
"""

from typing import Any, Dict, Optional
import json

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.user_type import user_type
from app.db.session import get_db
from app import schemas # スキーマをインポート
from app.services import user_type_service # user_type_service をインポート

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/user_type", response_class=HTMLResponse)
def get_user_type_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員種別管理ページを表示します"""
    user_types = user_type.get_multi(db)
    return templates.TemplateResponse(
        "pages/user_type.html", {"request": request, "user_types": user_types}
    )


@router.get("/user_types/modal", response_class=HTMLResponse)
@router.get("/user_types/modal/{user_type_id}", response_class=HTMLResponse)
async def user_type_modal(request: Request, user_type_id: Optional[int] = None, db: Session = Depends(get_db)) -> Any:
    """社員種別の追加または編集モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_type_id: 編集する場合の社員種別ID (None の場合は新規追加)
        db: データベースセッション

    Returns:
        HTMLResponse: モーダルHTMLフラグメント
    """
    user_type_data = None
    if user_type_id:
        user_type_data = user_type.get(db, id=user_type_id)
        if not user_type_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"UserType with id {user_type_id} not found")
    
    modal_id = "add-user-type" if user_type_id is None else f"edit-user-type-{user_type_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "user_type": user_type_data,
        "modal_id": modal_id,
        "errors": {}
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "partials/user_types/user_type_modal.html", ctx, headers=headers
    )


@router.get("/user_types/delete-modal/{user_type_id}", response_class=HTMLResponse)
async def user_type_delete_modal(request: Request, user_type_id: int, db: Session = Depends(get_db)) -> Any:
    """社員種別の削除確認モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_type_id: 削除する社員種別ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除確認モーダルHTMLフラグメント
    """
    user_type_data = user_type.get(db, id=user_type_id)
    if not user_type_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"UserType with id {user_type_id} not found")
        
    modal_id = f"user-type-delete-modal-{user_type_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "user_type": user_type_data,
        "modal_id": modal_id,
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "partials/user_types/user_type_delete_modal.html", ctx, headers=headers
    )


@router.post("/user_types", response_class=HTMLResponse)
async def create_user_type(
    request: Request,
    user_type_in: schemas.user_type.UserTypeCreate = Depends(schemas.user_type.UserTypeCreate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """新規社員種別を作成します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_type_in: 社員種別作成スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = "add-user-type"
    
    try:
        # 社員種別作成を試みる
        created_user_type = user_type_service.create_user_type_with_validation(db=db, user_type_in=user_type_in)
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "partials/user_types/user_type_modal.html",
            {
                "request": request,
                "user_type": created_user_type,
                "modal_id": modal_id
            },
            headers={
                "HX-Trigger": json.dumps({
                    "closeModal": modal_id,
                    "refreshPage": True
                })
            }
        )
    except HTTPException as e:
        # エラー時は同じモーダルを表示し、エラーメッセージを表示
        return templates.TemplateResponse(
            "partials/user_types/user_type_modal.html",
            {
                "request": request, 
                "user_type": None,
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.put("/user_types/{user_type_id}", response_class=HTMLResponse)
async def update_user_type(
    request: Request,
    user_type_id: int,
    user_type_in: schemas.user_type.UserTypeUpdate = Depends(schemas.user_type.UserTypeUpdate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """社員種別を更新します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_type_id: 更新する社員種別ID
        user_type_in: 社員種別更新スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = f"edit-user-type-{user_type_id}"
    
    try:
        # 社員種別更新を試みる
        updated_user_type = user_type_service.update_user_type_with_validation(
            db=db, user_type_id=user_type_id, user_type_in=user_type_in
        )
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "partials/user_types/user_type_modal.html",
            {
                "request": request,
                "user_type": updated_user_type,
                "modal_id": modal_id
            },
            headers={
                "HX-Trigger": json.dumps({
                    "closeModal": modal_id,
                    "refreshPage": True
                })
            }
        )
    except HTTPException as e:
        # エラー時は同じモーダルを表示し、エラーメッセージを表示
        return templates.TemplateResponse(
            "partials/user_types/user_type_modal.html",
            {
                "request": request, 
                "user_type": user_type.get(db, id=user_type_id),
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.delete("/user_types/{user_type_id}", response_class=HTMLResponse)
async def delete_user_type(request: Request, user_type_id: int, db: Session = Depends(get_db)) -> Any:
    """社員種別を削除します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_type_id: 削除する社員種別ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除完了後のレスポンス
    """
    try:
        # 社員種別が存在するか確認
        user_type_data = user_type.get(db, id=user_type_id)
        if not user_type_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"UserType with id {user_type_id} not found")
        
        # 社員種別の削除処理
        user_type.remove(db=db, id=user_type_id)
        
        # モーダルを閉じて画面をリロードするトリガーを返す
        modal_id = f"user-type-delete-modal-{user_type_id}"
        return HTMLResponse(
            content="",
            status_code=200,
            headers={
                "HX-Trigger": json.dumps({
                    "closeModal": modal_id,
                    "refreshPage": True
                })
            }
        )
    except HTTPException as e:
        # エラー時は同じモーダルを表示し、エラーメッセージを表示
        modal_id = f"user-type-delete-modal-{user_type_id}"
        ctx = {
            "request": request,
            "user_type": user_type.get(db, id=user_type_id),
            "modal_id": modal_id,
            "warning_message": e.detail
        }
        return templates.TemplateResponse(
            "partials/user_types/user_type_delete_modal.html", ctx
        )


@router.post("/pages/user_type/row", response_class=HTMLResponse)
def handle_create_user_type_row(
    request: Request,
    db: Session = Depends(get_db),
    user_type_in: schemas.user_type.UserTypeCreate = Depends(schemas.user_type.UserTypeCreate.as_form)
) -> Any:
    """新規社員種別を作成し、新しいテーブル行のHTMLフラグメントを返します。"""
    try:
        created_user_type = user_type_service.create_user_type_with_validation(db=db, user_type_in=user_type_in)
        # 作成成功時は、新しい行を描画して返す
        response = templates.TemplateResponse(
            "components/user_type/_user_type_row.html",
            {"request": request, "user_type": created_user_type}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"社員種別 {created_user_type.name} を追加しました。",
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


@router.put("/pages/user_type/row/{user_type_id}", response_class=HTMLResponse)
def handle_update_user_type_row(
    request: Request,
    user_type_id: int,
    db: Session = Depends(get_db),
    user_type_in: schemas.user_type.UserTypeUpdate = Depends(schemas.user_type.UserTypeUpdate.as_form)
) -> Any:
    """社員種別情報を更新し、更新されたテーブル行のHTMLフラグメントを返します。"""
    try:
        updated_user_type = user_type_service.update_user_type_with_validation(
            db=db, user_type_id=user_type_id, user_type_in=user_type_in
        )
        # 更新成功時は、更新された行を描画して返す
        response = templates.TemplateResponse(
            "components/user_type/_user_type_row.html",
            {"request": request, "user_type": updated_user_type}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"社員種別 {updated_user_type.name} を更新しました。",
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
        response.headers["HX-Retarget"] = f"#edit-form-error-{user_type_id}"
        # エラー時にもメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({"showMessage": e.detail, "isError": True})
        return response 