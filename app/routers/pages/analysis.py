"""勤怠集計page adapter。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import analysis_coverage_service, analysis_read_service
from app.utils.calendar_utils import get_current_month_formatted, parse_month

router = APIRouter(prefix="/analysis", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_analysis_page(
    request: Request,
    month: Optional[str] = None,
    year: Optional[int] = Query(default=None, ge=1900, le=2100),
    mode: Optional[str] = None,
    selected_locations: Optional[list[int]] = Query(default=None),
    show_total: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
) -> Any:
    """月次/年度の勤怠集計をrenderする。

    year指定またはmode=yearではmonthを参照しない。月次modeのmonthだけをcanonical化し、
    不正値はcurrent monthへredirectする。DB/internal failureはempty 200へ変換せず、
    application共通HTTP boundaryへ伝播させる。

    full page / period変更では「全合計」だけを初期表示する。location filter自身のHTMX
    requestではcheckbox parameterをそのままselectionとして扱い、全解除も表現できるようにする。
    """
    is_year_mode = year is not None or mode == "year"
    if month is not None and not is_year_mode:
        try:
            month_year, month_num = parse_month(month)
            month = f"{month_year}-{month_num:02d}"
        except ValueError:
            current_month = get_current_month_formatted()
            return RedirectResponse(url=f"/analysis?month={current_month}")

    is_htmx_request = request.headers.get("HX-Request") == "true"
    is_history_restore = request.headers.get("HX-History-Restore-Request") == "true"
    is_location_filter_request = (
        is_htmx_request
        and not is_history_restore
        and request.headers.get("HX-Target") == "analysis-table-region"
    )
    selected_location_ids = selected_locations or []
    include_total = (
        show_total if show_total is not None else not is_location_filter_request
    )

    view_model = analysis_read_service.get_analysis_page_view_model(
        db,
        month=month,
        year=year,
        mode=mode,
        selected_location_ids=selected_location_ids,
    )
    coverage_view_model = analysis_coverage_service.get_analysis_coverage_view_model(
        analysis_data=view_model["analysis_data"],
        group_sections=view_model["group_sections"],
        selected_location_ids=view_model["selected_location_ids"],
        is_year_mode=view_model["is_year_mode"],
        include_total=include_total,
    )
    context = {
        "request": request,
        **view_model,
        **coverage_view_model,
    }

    if is_htmx_request and not is_history_restore:
        template_name = (
            "components/analysis/table_region.html"
            if is_location_filter_request
            else "components/analysis/content.html"
        )
        return templates.TemplateResponse(
            template_name,
            context,
        )

    return templates.TemplateResponse(
        "pages/analysis.html",
        context,
    )
