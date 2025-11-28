"""
勤怠種別管理ページエンドポイント
----------------

勤怠種別の設定管理に関連するルートハンドラー
"""

from typing import Any, Dict, List, Optional
import json
from collections import defaultdict

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
router = APIRouter(prefix="/ui/locations", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_location_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """勤怠種別管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    locations = location.get_multi(db)
    
    # 分類ごとにグルーピング
    grouped_locations = defaultdict(list)
    category_names = []
    
    for loc in locations:
        category = loc.category or "未分類"
        if category not in category_names:
            category_names.append(category)
        grouped_locations[category].append(loc)
    
    return templates.TemplateResponse(
        "pages/location.html", {
            "request": request, 
            "locations": locations,  # すべての勤怠種別（従来の互換性のため）
            "category_names": category_names,  # 分類名のリスト
            "grouped_locations": grouped_locations  # 分類ごとの勤怠種別
        }
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{location_id}", response_class=HTMLResponse)
async def location_modal(request: Request, location_id: Optional[int] = None, db: Session = Depends(get_db)) -> Any:
    """勤怠種別の追加または編集モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 編集する場合の勤怠種別ID (None の場合は新規追加)
        db: データベースセッション

    Returns:
        HTMLResponse: モーダルHTMLフラグメント
    """
    location_data = None
    if location_id:
        location_data = location.get(db, id=location_id)
        if not location_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with id {location_id} not found")
    
    modal_id = "add-location" if location_id is None else f"edit-location-{location_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "location": location_data,
        "modal_id": modal_id,
        "errors": {}
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "components/partials/modals/location_modal.html", ctx, headers=headers
    )


@router.get("/delete-modal/{location_id}", response_class=HTMLResponse)
async def location_delete_modal(request: Request, location_id: int, db: Session = Depends(get_db)) -> Any:
    """勤怠種別の削除確認モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 削除する勤怠種別ID
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
        "components/partials/modals/location_delete_modal.html", ctx, headers=headers
    )


@router.post("", response_class=HTMLResponse)
async def create_location(
    request: Request,
    location_in: schemas.location.LocationCreate = Depends(schemas.location.LocationCreate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """新規勤怠種別を作成します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_in: 勤怠種別作成スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = "add-location" 
    
    try:
        # 勤怠種別作成を試みる
        created_location = location_service.create_location_with_validation(db=db, location_in=location_in)
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "components/partials/modals/location_modal.html",
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
            "components/partials/modals/location_modal.html",
            {
                "request": request, 
                "location": None,
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.put("/{location_id}", response_class=HTMLResponse)
async def update_location(
    request: Request,
    location_id: int,
    location_in: schemas.location.LocationUpdate = Depends(schemas.location.LocationUpdate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """勤怠種別を更新します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 更新する勤怠種別ID
        location_in: 勤怠種別更新スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = f"edit-location-{location_id}" 
    
    try:
        # 勤怠種別更新を試みる
        updated_location = location_service.update_location_with_validation(
            db=db, location_id=location_id, location_in=location_in
        )
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "components/partials/modals/location_modal.html",
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
            "components/partials/modals/location_modal.html",
            {
                "request": request, 
                "location": location.get(db, id=location_id),
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.delete("/{location_id}", response_class=HTMLResponse)
async def delete_location(request: Request, location_id: int, db: Session = Depends(get_db)) -> Any:
    """勤怠種別を削除します。

    Args:
        request: FastAPIリクエストオブジェクト
        location_id: 削除する勤怠種別ID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除完了後のレスポンス
    """
    try:
        # 勤怠種別が存在するか確認
        location_data = location.get(db, id=location_id)
        if not location_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Location with id {location_id} not found")
        
        # 勤怠種別の削除処理
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
            "components/partials/modals/location_delete_modal.html", ctx
        )


@router.post("/rows", response_class=HTMLResponse)
def handle_create_location_row(
    request: Request,
    db: Session = Depends(get_db),
    location_in: schemas.location.LocationCreate = Depends(schemas.location.LocationCreate.as_form)
) -> Any:
    """新規勤怠種別を作成し、新しいテーブル行のHTMLフラグメントを返します。"""
    try:
        created_location = location_service.create_location_with_validation(db=db, location_in=location_in)
        # 作成成功時は、新しい行を描画して返す
        response = templates.TemplateResponse(
            "components/location/_location_row.html",
            {"request": request, "location": created_location}
        )
        # 成功時にページリフレッシュとメッセージ表示をトリガー
        response.headers["HX-Trigger"] = json.dumps({
            "showMessage": f"勤怠種別 {created_location.name} を追加しました。",
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


@router.put("/rows/{location_id}", response_class=HTMLResponse)
def handle_update_location_row(
    request: Request,
    location_id: int,
    db: Session = Depends(get_db),
    location_in: schemas.location.LocationUpdate = Depends(schemas.location.LocationUpdate.as_form)
) -> Any:
    """勤怠種別情報を更新し、更新されたテーブル行のHTMLフラグメントを返します。"""
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
            "showMessage": f"勤怠種別 {updated_location.name} を更新しました。",
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
