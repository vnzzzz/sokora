"""勤怠weekly page/HTMX adapter。"""

import json
import logging
from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.attendance import attendance
from app.crud.location import location as location_crud
from app.crud.user import user
from app.db.session import get_db
from app.models.attendance import Attendance as AttendanceModel
from app.models.location import Location
from app.services import attendance_read_service
from app.utils.calendar_utils import (
    format_date_jp,
    get_current_week_formatted,
    parse_week,
)

router = APIRouter(prefix="/attendance", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/weekly", response_class=HTMLResponse)
def attendance_page(
    request: Request,
    search_query: Optional[str] = None,
    week: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """weekly attendance matrixをrenderする。"""
    if week is None:
        week = get_current_week_formatted()
    else:
        try:
            week = parse_week(week).isoformat()
        except ValueError as exc:
            logger.warning("無効な週パラメータ '%s': %s", week, exc)
            current_week = get_current_week_formatted()
            return RedirectResponse(url=f"/attendance/weekly?week={current_week}")

    view_model = attendance_read_service.get_weekly_page_view_model(
        db,
        week=week,
        search_query=search_query,
    )
    context = {"request": request, **view_model}

    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            "components/partials/attendance/calendar.html",
            context,
            headers={"HX-Reswap": "outerHTML"},
        )
    return templates.TemplateResponse("pages/attendance.html", context)


@router.get("/modals/{user_id}/{date_str}", response_class=HTMLResponse)
def get_attendance_modal(
    request: Request,
    user_id: str,
    date_str: str,  # パスパラメータは YYYY-MM-DD 形式を期待
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """指定されたユーザーと日付の勤怠編集モーダルを返します。

    Args:
        request: FastAPIリクエストオブジェクト
        user_id: 編集対象のユーザーID
        date_str: 編集対象の日付（YYYY-MM-DD形式）
        mode: モード指定（registerの場合は登録用モーダル）
        db: データベースセッション

    Returns:
        HTMLResponse: レンダリングされたHTMLページ
    """
    logger.info(
        f"勤怠モーダルリクエスト受信: User={user_id}, Date={date_str}, Mode={mode}"
    )
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        logger.warning(f"無効な日付形式: {date_str}")
        # エラーを示す空のコンテナを返すか、エラーメッセージを含むHTMLを返す
        return HTMLResponse(content="", status_code=status.HTTP_400_BAD_REQUEST)

    user_obj = user.get(db, id=user_id)
    if not user_obj:
        logger.warning(f"ユーザーが見つかりません: {user_id}")
        return HTMLResponse(content="", status_code=status.HTTP_404_NOT_FOUND)

    # 既存の勤怠データを取得 (CRUD関数名を修正)
    attendance_obj: Optional[AttendanceModel] = attendance.get_by_user_and_date(
        db, user_id=user_id, date=target_date
    )
    attendance_id = attendance_obj.id if attendance_obj else None
    current_location_id = attendance_obj.location_id if attendance_obj else None
    note = attendance_obj.note if attendance_obj else None  # 備考フィールドを取得

    # 全勤怠種別を取得
    locations: List[Location] = location_crud.list_all(db)

    # マクロを使用するためのコンテキストを作成
    context = {
        "request": request,
        "attendance_modal_params": {
            "user_id": user_id,
            "date": date_str,
            "user_name": str(user_obj.username),
            "formatted_date": format_date_jp(target_date),
            "attendance_id": attendance_id,
            "current_location_id": current_location_id,
            "locations": locations,
            "mode": mode,  # モード情報を追加
            "note": note,  # 備考フィールドを追加
        },
    }
    logger.debug(f"モーダルコンテキスト: {context}")

    modal_id = f"attendance-modal-{user_id}-{date_str}"
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}

    # マクロを直接呼び出して表示
    return templates.TemplateResponse(
        "components/partials/modals/attendance_modal.html", context, headers=headers
    )
