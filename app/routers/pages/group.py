"""
グループ管理ページエンドポイント
----------------

グループの設定管理に関連するルートハンドラー
"""

from typing import Any, Dict, Optional, Union
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


@router.get("/groups/modal", response_class=HTMLResponse)
@router.get("/groups/modal/{group_id}", response_class=HTMLResponse)
async def group_modal(request: Request, group_id: Optional[int] = None, db: Session = Depends(get_db)) -> Any:
    """グループの追加または編集モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        group_id: 編集する場合のグループID (None の場合は新規追加)
        db: データベースセッション

    Returns:
        HTMLResponse: モーダルHTMLフラグメント
    """
    group_data = None
    if group_id:
        group_data = group.get(db, id=group_id)
        if not group_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group with id {group_id} not found")
    
    modal_id = "add-group" if group_id is None else f"edit-group-{group_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "group": group_data,
        "modal_id": modal_id,
        "errors": {}
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "partials/groups/group_modal.html", ctx, headers=headers
    )


@router.get("/groups/delete-modal/{group_id}", response_class=HTMLResponse)
async def group_delete_modal(request: Request, group_id: int, db: Session = Depends(get_db)) -> Any:
    """グループの削除確認モーダルを表示します。

    Args:
        request: FastAPIリクエストオブジェクト
        group_id: 削除するグループID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除確認モーダルHTMLフラグメント
    """
    group_data = group.get(db, id=group_id)
    if not group_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group with id {group_id} not found")
    
    # 所属ユーザーの有無をチェック（オプション）
    
    modal_id = f"group-delete-modal-{group_id}"
    
    ctx: Dict[str, Any] = {
        "request": request,
        "group": group_data,
        "modal_id": modal_id,
    }
    
    # JSONオブジェクトとして正しい形式のトリガーを返す
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}
    return templates.TemplateResponse(
        "partials/groups/group_delete_modal.html", ctx, headers=headers
    )


@router.delete("/groups/{group_id}", response_class=HTMLResponse)
async def delete_group(request: Request, group_id: int, db: Session = Depends(get_db)) -> Any:
    """グループを削除します。

    Args:
        request: FastAPIリクエストオブジェクト
        group_id: 削除するグループID
        db: データベースセッション

    Returns:
        HTMLResponse: 削除完了後のレスポンス
    """
    try:
        # グループが存在するか確認
        group_data = group.get(db, id=group_id)
        if not group_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group with id {group_id} not found")
        
        # グループの削除処理
        group.remove(db=db, id=group_id)
        
        # モーダルを閉じて画面をリロードするトリガーを返す
        modal_id = f"group-delete-modal-{group_id}"
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
        modal_id = f"group-delete-modal-{group_id}"
        ctx = {
            "request": request,
            "group": group.get(db, id=group_id),
            "modal_id": modal_id,
            "warning_message": e.detail
        }
        return templates.TemplateResponse(
            "partials/groups/group_delete_modal.html", ctx
        )


@router.post("/groups", response_class=HTMLResponse)
async def create_group(
    request: Request,
    group_in: schemas.GroupCreate = Depends(schemas.GroupCreate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """新規グループを作成します。

    Args:
        request: FastAPIリクエストオブジェクト
        group_in: グループ作成スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = "add-group"  
    
    try:
        # グループ作成を試みる
        created_group = group_service.create_group_with_validation(db=db, group_in=group_in)
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "partials/groups/group_modal.html",
            {
                "request": request,
                "group": created_group,
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
            "partials/groups/group_modal.html",
            {
                "request": request, 
                "group": None,
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        )


@router.put("/groups/{group_id}", response_class=HTMLResponse)
async def update_group(
    request: Request,
    group_id: int,
    group_in: schemas.GroupUpdate = Depends(schemas.GroupUpdate.as_form),
    db: Session = Depends(get_db)
) -> Any:
    """グループを更新します。

    Args:
        request: FastAPIリクエストオブジェクト
        group_id: 更新するグループID
        group_in: グループ更新スキーマ（フォームデータ）
        db: データベースセッション

    Returns:
        HTMLResponse: 更新されたモーダル、エラー時はエラーメッセージを含むモーダル
    """
    modal_id = f"edit-group-{group_id}" 
    
    try:
        # グループ更新を試みる
        updated_group = group_service.update_group_with_validation(
            db=db, group_id=group_id, group_in=group_in
        )
        
        # 成功時はモーダルを閉じてページリフレッシュするトリガーを送信
        return templates.TemplateResponse(
            "partials/groups/group_modal.html",
            {
                "request": request,
                "group": updated_group,
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
            "partials/groups/group_modal.html",
            {
                "request": request, 
                "group": group.get(db, id=group_id),
                "modal_id": modal_id,
                "errors": {"name": [e.detail]}
            }
        ) 