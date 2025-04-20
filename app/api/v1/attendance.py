"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するAPIエンドポイント
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse
from typing import Any
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.attendance import attendance

# API用ルーター
router = APIRouter(prefix="/api", tags=["Attendance"])


@router.post("/attendance/update", response_class=RedirectResponse)
async def update_attendance(
    request: Request,
    user_id: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """ユーザーの勤務場所を更新します

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 更新するユーザーID（フォームデータ）
        date: 更新する日付（フォームデータ）
        location: 更新する勤務場所（フォームデータ）
        db: データベースセッション

    Returns:
        RedirectResponse: ユーザー編集ページへのリダイレクト
    """
    try:
        success = attendance.update_user_entry(
            db, user_id=user_id, date_str=date, location=location
        )
        if not success:
            raise HTTPException(
                status_code=400,
                detail="勤怠データの更新に失敗しました。ユーザーIDまたは日付が無効である可能性があります。"
            )
        return RedirectResponse(url=f"/attendance/edit/{user_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
