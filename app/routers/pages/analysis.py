"""勤怠集計page adapter。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import analysis_read_service
from app.utils.calendar_utils import get_current_month_formatted, parse_month

router = APIRouter(prefix="/analysis", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_analysis_page(
    request: Request,
    month: Optional[str] = None,
    year: Optional[int] = Query(default=None, ge=1900, le=2100),
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """月次/年度の勤怠集計をrenderする。

    year指定またはmode=yearではmonthを参照しない。月次modeのmonthだけをcanonical化し、
    不正値はcurrent monthへredirectする。DB/internal failureはempty 200へ変換せず、
    application共通HTTP boundaryへ伝播させる。
    """
    is_year_mode = year is not None or mode == "year"
    if month is not None and not is_year_mode:
        try:
            month_year, month_num = parse_month(month)
            month = f"{month_year}-{month_num:02d}"
        except ValueError:
            current_month = get_current_month_formatted()
            return RedirectResponse(url=f"/analysis?month={current_month}")

    view_model = analysis_read_service.get_analysis_page_view_model(
        db,
        month=month,
        year=year,
        mode=mode,
    )
    return templates.TemplateResponse(
        "pages/analysis.html",
        {"request": request, **view_model},
    )
