"""
勤怠管理関連エンドポイント
----------------

勤怠入力と編集に関連するルートハンドラー
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Any
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...crud.user import user
from ...crud.attendance import attendance
from ...crud.location import location
from ..v1.calendar import build_calendar_data
from ...utils.date_utils import (
    get_today_formatted,
    get_current_month_formatted,
    get_last_viewed_date,
)
from ...utils.ui_utils import generate_location_styles
from ...utils.calendar_utils import (
    parse_month,
    get_prev_month_date,
    get_next_month_date,
)

# API用ルーター
router = APIRouter(prefix="/api", tags=["Attendance"])
# ページ表示用ルーター
page_router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@page_router.get("/employee", response_class=HTMLResponse)
def employee_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """従業員管理ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    users = user.get_all_users(db)
    return templates.TemplateResponse(
        "employee.html", {"request": request, "users": users}
    )


@page_router.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """勤怠登録ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    users = user.get_all_users(db)
    return templates.TemplateResponse(
        "attendance.html", {"request": request, "users": users}
    )


@page_router.get("/attendance/edit/{user_id}", response_class=HTMLResponse)
def edit_user_attendance(
    request: Request,
    user_id: str,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """ユーザーの勤怠編集ページを表示します

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 編集対象のユーザーID
        month: 月（YYYY-MM形式、指定がない場合は現在の月）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    if month is None:
        month = get_current_month_formatted()

    # Get calendar data for the specified month
    calendar_data = build_calendar_data(db, month)

    # Get user name
    user_name = user.get_user_name_by_id(db, user_id=user_id)

    # Get user data
    user_entries = attendance.get_user_data(db, user_id=user_id)
    all_users = user.get_all_users(db)
    all_user_ids = [user_id for user_name, user_id in all_users]

    if not user_entries and user_id not in all_user_ids:
        raise HTTPException(status_code=404, detail=f"User ID '{user_id}' not found")

    # Create a map of dates and work locations for the user
    user_dates = []
    user_locations = {}
    for entry in user_entries:
        date = entry["date"]
        user_dates.append(date)
        user_locations[date] = entry["location"]

    # Get types of work locations
    location_types = location.get_all_locations(db)

    # Generate style information for work locations
    location_styles = generate_location_styles(location_types)

    # 前月と翌月の情報はcalendar_dataから取得可能
    prev_month = calendar_data["prev_month"]
    next_month = calendar_data["next_month"]

    context = {
        "request": request,
        "user_id": user_id,
        "user_name": user_name,
        "calendar_data": calendar_data["weeks"],
        "user_dates": user_dates,
        "user_locations": user_locations,
        "location_styles": location_styles,
        "location_types": location_types,
        "prev_month": prev_month,
        "next_month": next_month,
        "month_name": calendar_data["month_name"],
    }

    return templates.TemplateResponse("attendance_edit.html", context)


# API endpoints
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
