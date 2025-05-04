"""
グループ管理ページエンドポイント
----------------

グループの設定管理に関連するルートハンドラー
"""

from typing import Any
import json

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.group import group
from app.db.session import get_db
from app import schemas # スキーマをインポート
from app.services import group_service # group_service をインポート

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/group", response_class=HTMLResponse)
def group_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """グループ管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    groups = group.get_multi(db)
    return templates.TemplateResponse(
        "pages/group.html", {"request": request, "groups": groups}
    )


@router.get("/pages/group/edit/{group_id}", response_class=HTMLResponse)
def get_group_edit_form(request: Request, group_id: int, db: Session = Depends(get_db)) -> Any:
    """指定されたグループの編集フォームをHTMLフラグメントとして返します。"""
    group_data = group.get(db, id=group_id)
    if not group_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group with id {group_id} not found")

    return templates.TemplateResponse(
        "components/group/_group_edit_form.html",
        {
            "request": request,
            "group": group_data,
        }
    )


@router.post("/pages/group/row", response_class=HTMLResponse)
def handle_create_group_row(
    request: Request,
    db: Session = Depends(get_db),
    group_in: schemas.GroupCreate = Depends(schemas.GroupCreate.as_form)
) -> Any:
    """新規グループを作成し、新しいテーブル行のHTMLフラグメントを返します。"""
    try:
        created_group = group_service.create_group_with_validation(db=db, group_in=group_in)
        # 作成成功時は、新しい行を描画して返す
        response = templates.TemplateResponse(
            "components/group/_group_row.html",
            {"request": request, "group": created_group}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"グループ {created_group.name} を追加しました。",
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


@router.put("/pages/group/row/{group_id}", response_class=HTMLResponse)
def handle_update_group_row(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
    group_in: schemas.GroupUpdate = Depends(schemas.GroupUpdate.as_form)
) -> Any:
    """グループ情報を更新し、更新されたテーブル行のHTMLフラグメントを返します。"""
    try:
        updated_group = group_service.update_group_with_validation(
            db=db, group_id=group_id, group_in=group_in
        )
        # 更新成功時は、更新された行を描画して返す
        response = templates.TemplateResponse(
            "components/group/_group_row.html",
            {"request": request, "group": updated_group}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"グループ {updated_group.name} を更新しました。",
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
        response.headers["HX-Retarget"] = f"#edit-form-error-{group_id}"
        # エラー時にもメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({"showMessage": e.detail, "isError": True})
        return response 