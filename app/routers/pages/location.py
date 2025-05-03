"""
勤務場所管理ページエンドポイント
----------------

勤務場所の設定管理に関連するルートハンドラー
"""

from typing import Any, Dict, List
import json

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.location import location
from app.db.session import get_db
from app import schemas # スキーマをインポート
from app.services import location_service # location_service をインポート
from app.utils.ui_utils import TAILWIND_COLORS

# ルーター定義
router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/location", response_class=HTMLResponse)
def get_location_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """勤務場所管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    locations = location.get_multi(db)
    return templates.TemplateResponse(
        "pages/location/index.html", {"request": request, "locations": locations}
    )


@router.get("/pages/location/edit/{location_id}", response_class=HTMLResponse)
def get_location_edit_form(request: Request, location_id: int, db: Session = Depends(get_db)) -> Any:
    """指定された勤務場所の編集フォームをHTMLフラグメントとして返します。"""
    location_data = location.get(db, id=location_id)
    if not location_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with id {location_id} not found")

    return templates.TemplateResponse(
        "components/location/_location_edit_form.html",
        {
            "request": request,
            "location": location_data,
        }
    )


@router.post("/pages/location/row", response_class=HTMLResponse)
def handle_create_location_row(
    request: Request,
    db: Session = Depends(get_db),
    location_in: schemas.location.LocationCreate = Depends(schemas.location.LocationCreate.as_form)
) -> Any:
    """新規勤務場所を作成し、新しいテーブル行のHTMLフラグメントを返します。"""
    try:
        created_location = location_service.create_location_with_validation(db=db, location_in=location_in)
        # 作成成功時は、新しい行を描画して返す
        response = templates.TemplateResponse(
            "components/location/_location_row.html",
            {"request": request, "location": created_location}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"勤務場所 {created_location.name} を追加しました。",
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


@router.put("/pages/location/row/{location_id}", response_class=HTMLResponse)
def handle_update_location_row(
    request: Request,
    location_id: int,
    db: Session = Depends(get_db),
    location_in: schemas.location.LocationUpdate = Depends(schemas.location.LocationUpdate.as_form)
) -> Any:
    """勤務場所情報を更新し、更新されたテーブル行のHTMLフラグメントを返します。"""
    try:
        updated_location = location_service.update_location_with_validation(
            db=db, location_id=location_id, location_in=location_in
        )
        # 更新成功時は、更新された行を描画して返す
        response = templates.TemplateResponse(
            "components/location/_location_row.html",
            {"request": request, "location": updated_location}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"勤務場所 {updated_location.name} を更新しました。",
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
        response.headers["HX-Retarget"] = f"#edit-form-error-{location_id}"
        # エラー時にもメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({"showMessage": e.detail, "isError": True})
        return response 