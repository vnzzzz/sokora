"""祝日管理ページエンドポイント。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import schemas
from app.crud import custom_holiday as crud_custom_holiday
from app.db.session import get_db
from app.models import CustomHoliday
from app.routers.pages.master_crud import MasterCrudResponder
from app.services import custom_holiday_service
from app.services.errors import ApplicationError
from app.utils.holiday_cache import get_cache_info

router = APIRouter(prefix="/holidays", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
responder = MasterCrudResponder(
    templates=templates,
    form_template="components/partials/modals/custom_holiday_modal.html",
    delete_template="components/partials/modals/custom_holiday_delete_modal.html",
)


def _get_holiday_or_404(db: Session, holiday_id: int) -> CustomHoliday:
    holiday = crud_custom_holiday.get(db, id=holiday_id)
    if holiday is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="祝日が見つかりません",
        )
    return holiday


def _holiday_error_field(detail: str) -> str:
    return "date" if "日付" in detail else "name"


@router.get("", response_class=HTMLResponse)
def get_holiday_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """祝日管理ページを表示する。"""
    custom_holidays = crud_custom_holiday.get_multi(db)
    cache_info = get_cache_info()
    built_in_total = cache_info.get("total_holidays", 0) - cache_info.get(
        "custom_total", 0
    )
    return templates.TemplateResponse(
        "pages/holiday.html",
        {
            "request": request,
            "custom_holidays": custom_holidays,
            "cache_info": cache_info,
            "built_in_total": built_in_total,
        },
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{holiday_id}", response_class=HTMLResponse)
async def custom_holiday_modal(
    request: Request,
    holiday_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """追加・編集モーダルを返す。"""
    holiday = _get_holiday_or_404(db, holiday_id) if holiday_id is not None else None
    modal_id = (
        "add-custom-holiday"
        if holiday_id is None
        else f"edit-custom-holiday-{holiday_id}"
    )
    return responder.open_form(
        request,
        modal_id=modal_id,
        context={"holiday": holiday},
    )


@router.get("/delete-modal/{holiday_id}", response_class=HTMLResponse)
async def custom_holiday_delete_modal(
    request: Request,
    holiday_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """削除確認モーダルを返す。"""
    holiday = _get_holiday_or_404(db, holiday_id)
    return responder.open_delete(
        request,
        modal_id=f"custom-holiday-delete-modal-{holiday_id}",
        context={"holiday": holiday},
    )


@router.post("", response_class=HTMLResponse)
async def create_custom_holiday(
    request: Request,
    holiday_in: schemas.custom_holiday.CustomHolidayCreate = Depends(
        schemas.custom_holiday.CustomHolidayCreate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """祝日を作成し、標準master CRUD triggerを返す。"""
    modal_id = "add-custom-holiday"
    try:
        created = custom_holiday_service.create_custom_holiday_with_validation(
            db,
            custom_holiday_in=holiday_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"holiday": created},
            message=f"祝日 {created.name} を追加しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        detail = str(exc.detail)
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"holiday": None},
            errors={_holiday_error_field(detail): [detail]},
        )


@router.put("/{holiday_id}", response_class=HTMLResponse)
async def update_custom_holiday(
    request: Request,
    holiday_id: int,
    holiday_in: schemas.custom_holiday.CustomHolidayUpdate = Depends(
        schemas.custom_holiday.CustomHolidayUpdate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """祝日を更新し、標準master CRUD triggerを返す。"""
    modal_id = f"edit-custom-holiday-{holiday_id}"
    try:
        updated = custom_holiday_service.update_custom_holiday_with_validation(
            db,
            custom_holiday_id=holiday_id,
            custom_holiday_in=holiday_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"holiday": updated},
            message=f"祝日 {updated.name} を更新しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        detail = str(exc.detail)
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"holiday": crud_custom_holiday.get(db, id=holiday_id)},
            errors={_holiday_error_field(detail): [detail]},
        )


@router.delete("/{holiday_id}", response_class=HTMLResponse)
async def delete_custom_holiday(
    request: Request,
    holiday_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """祝日を削除し、標準master CRUD triggerを返す。"""
    modal_id = f"custom-holiday-delete-modal-{holiday_id}"
    holiday = _get_holiday_or_404(db, holiday_id)
    holiday_name = str(holiday.name)
    try:
        custom_holiday_service.delete_custom_holiday(
            db,
            custom_holiday_id=holiday_id,
        )
        return responder.delete_success(
            modal_id=modal_id,
            message=f"祝日 {holiday_name} を削除しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.delete_error(
            request,
            modal_id=modal_id,
            context={"holiday": crud_custom_holiday.get(db, id=holiday_id)},
            warning_message=str(exc.detail),
        )
