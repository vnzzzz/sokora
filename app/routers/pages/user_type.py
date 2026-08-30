"""
社員種別管理ページエンドポイント
----------------

社員種別の設定管理に関連するルートハンドラー
"""

from typing import Any
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


@router.get("/user_types", response_class=HTMLResponse)
def get_user_type_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員種別管理ページを表示します"""
    user_types = user_type.get_multi(db)
    return templates.TemplateResponse(
        "pages/user_type/index.html", {"request": request, "user_types": user_types}
    )


@router.get("/pages/user_type/edit/{user_type_id}", response_class=HTMLResponse)
def get_user_type_edit_form(request: Request, user_type_id: int, db: Session = Depends(get_db)) -> Any:
    """指定された社員種別の編集フォームをHTMLフラグメントとして返します。"""
    user_type_data = user_type.get(db, id=user_type_id)
    if not user_type_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"UserType with id {user_type_id} not found")

    return templates.TemplateResponse(
        "components/user_type/_user_type_edit_form.html",
        {
            "request": request,
            "user_type": user_type_data,
        }
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