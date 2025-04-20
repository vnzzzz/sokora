"""
ユーザー管理APIエンドポイント
=====================

ユーザーの取得、作成、更新、削除のためのAPIエンドポイント。
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from typing import Any
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user import user

# API用ルーター
router = APIRouter(prefix="/api", tags=["Users"])


@router.post("/user/add", response_class=RedirectResponse)
async def add_user(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """新しいユーザーを追加します

    Args:
        request: FastAPIリクエストオブジェクト
        username: 追加するユーザー名（フォームデータ）
        user_id: ユーザーID（フォームデータ）
        db: データベースセッション

    Returns:
        RedirectResponse: 従業員管理ページへのリダイレクト
    """
    try:
        user.create_user(db, username=username, user_id=user_id)
        return RedirectResponse(url="/employee", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/update/{user_id}", response_class=RedirectResponse)
async def update_user(
    request: Request,
    user_id: str,
    username: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """ユーザー情報を更新します

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 更新するユーザーID
        username: 新しいユーザー名（フォームデータ）
        db: データベースセッション

    Returns:
        RedirectResponse: 従業員管理ページへのリダイレクト
    """
    try:
        success = user.update_user(db, user_id=user_id, username=username)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"ユーザー '{user_id}' の更新に失敗しました。"
            )
        return RedirectResponse(url="/employee", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/delete/{user_id}", response_class=RedirectResponse)
async def delete_user(
    request: Request, user_id: str, db: Session = Depends(get_db)
) -> RedirectResponse:
    """ユーザーを削除します

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 削除するユーザーID
        db: データベースセッション

    Returns:
        RedirectResponse: 従業員管理ページへのリダイレクト
    """
    try:
        user.delete_user(db, user_id=user_id)
        return RedirectResponse(url="/employee", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 