"""
勤務場所管理ページエンドポイント
----------------

勤務場所の設定管理に関連するルートハンドラー
"""

from typing import Any, Dict, List, Optional
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
        "pages/location.html", {"request": request, "locations": locations}
    )


@router.get("/locations/modal", response_class=HTMLResponse)
@router.get("/locations/modal/{location_id}", response_class=HTMLResponse)
async def location_modal(request: Request, location_id: Optional[int] = None, db: Session = Depends(get_db)) -> Any:
    """勤務場所の追加または編集モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 編集する場合の勤務場所ID (None の場合は新規追加)
        db: データベースセッション

    Returns:
        HTMLResponse: モーダルHTMLフラグメント
    """
    location_data = None
    if location_id:
        location_data = location.get(db, id=location_id)
        if not location_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with id {location_id} not found")
    
    modal_id = f"location-modal-{location_id or 'new'}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "location": location_data,
        "modal_id": modal_id,
        "errors": {}
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "partials/locations/location_modal.html", ctx, headers=headers
    )


@router.get("/locations/delete-modal/{location_id}", response_class=HTMLResponse)
async def location_delete_modal(request: Request, location_id: int, db: Session = Depends(get_db)) -> Any:
    """勤務場所の削除確認モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 削除する勤務場所ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除確認モーダルHTMLフラグメント
    """
    location_data = location.get(db, id=location_id)
    if not location_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with id {location_id} not found")
    
    modal_id = f"location-delete-modal-{location_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "location": location_data,
        "modal_id": modal_id,
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "partials/locations/location_delete_modal.html", ctx, headers=headers
    )


@router.post("/locations", response_class=HTMLResponse)
async def create_location(
    request: Request,
    location_in: schemas.location.LocationCreate = Depends(schemas.location.LocationCreate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """新規勤務場所を作成します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_in: 勤務場所作成スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = "location-modal-new"
    
    try:
        # 勤務場所作成を試みる
        created_location = location_service.create_location_with_validation(db=db, location_in=location_in)
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "partials/locations/location_modal.html",
            {
                "request": request,
                "location": created_location,
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
            "partials/locations/location_modal.html",
            {
                "request": request, 
                "location": None,
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.put("/locations/{location_id}", response_class=HTMLResponse)
async def update_location(
    request: Request,
    location_id: int,
    location_in: schemas.location.LocationUpdate = Depends(schemas.location.LocationUpdate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """勤務場所を更新します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 更新する勤務場所ID
        location_in: 勤務場所更新スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = f"location-modal-{location_id}"
    
    try:
        # 勤務場所更新を試みる
        updated_location = location_service.update_location_with_validation(
            db=db, location_id=location_id, location_in=location_in
        )
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "partials/locations/location_modal.html",
            {
                "request": request,
                "location": updated_location,
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
            "partials/locations/location_modal.html",
            {
                "request": request, 
                "location": location.get(db, id=location_id),
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.delete("/locations/{location_id}", response_class=HTMLResponse)
async def delete_location(request: Request, location_id: int, db: Session = Depends(get_db)) -> Any:
    """勤務場所を削除します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 削除する勤務場所ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除完了後のレスポンス
    """
    try:
        # 勤務場所が存在するか確認
        location_data = location.get(db, id=location_id)
        if not location_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with id {location_id} not found")
        
        # 勤務場所の削除処理
        location.remove(db=db, id=location_id)
        
        # モーダルを閉じて画面をリロードするトリガーを返す
        modal_id = f"location-delete-modal-{location_id}"
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
        modal_id = f"location-delete-modal-{location_id}"
        ctx = {
            "request": request,
            "location": location.get(db, id=location_id),
            "modal_id": modal_id,
            "warning_message": e.detail
        }
        return templates.TemplateResponse(
            "partials/locations/location_delete_modal.html", ctx
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