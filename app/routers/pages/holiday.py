"""
祝日管理ページエンドポイント
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import schemas
from app.crud import custom_holiday as crud_custom_holiday
from app.db.session import get_db
from app.services import custom_holiday_service
from app.utils.holiday_cache import get_cache_info

router = APIRouter(prefix="/holidays", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def get_holiday_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """祝日管理ページ"""
    custom_holidays = crud_custom_holiday.get_multi(db)
    cache_info = get_cache_info()
    built_in_total = cache_info.get("total_holidays", 0) - cache_info.get("custom_total", 0)

    context = {
        "request": request,
        "custom_holidays": custom_holidays,
        "cache_info": cache_info,
        "built_in_total": built_in_total,
    }
    return templates.TemplateResponse("pages/holiday.html", context)


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{holiday_id}", response_class=HTMLResponse)
async def custom_holiday_modal(
    request: Request,
    holiday_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """追加/編集モーダル"""
    holiday = None
    if holiday_id:
        holiday = crud_custom_holiday.get(db, id=holiday_id)
        if not holiday:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="祝日が見つかりません")

    modal_id = "add-custom-holiday" if holiday is None else f"edit-custom-holiday-{holiday.id}"
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}

    return templates.TemplateResponse(
        "components/partials/modals/custom_holiday_modal.html",
        {
            "request": request,
            "holiday": holiday,
            "modal_id": modal_id,
            "errors": {},
        },
        headers=headers,
    )


@router.get("/delete-modal/{holiday_id}", response_class=HTMLResponse)
async def custom_holiday_delete_modal(
    request: Request,
    holiday_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """削除確認モーダル"""
    holiday = crud_custom_holiday.get(db, id=holiday_id)
    if not holiday:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="祝日が見つかりません")

    modal_id = f"custom-holiday-delete-modal-{holiday.id}"
    headers = {"HX-Trigger": json.dumps({"openModal": modal_id})}

    return templates.TemplateResponse(
        "components/partials/modals/custom_holiday_delete_modal.html",
        {
            "request": request,
            "holiday": holiday,
            "modal_id": modal_id,
        },
        headers=headers,
    )


@router.post("", response_class=HTMLResponse)
async def create_custom_holiday(
    request: Request,
    holiday_in: schemas.custom_holiday.CustomHolidayCreate = Depends(
        schemas.custom_holiday.CustomHolidayCreate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """祝日追加"""
    modal_id = "add-custom-holiday"
    try:
        created = custom_holiday_service.create_custom_holiday_with_validation(db, custom_holiday_in=holiday_in)
        return templates.TemplateResponse(
            "components/partials/modals/custom_holiday_modal.html",
            {"request": request, "holiday": created, "modal_id": modal_id},
            headers={"HX-Trigger": json.dumps({"closeModal": modal_id, "refreshPage": True})},
        )
    except HTTPException as e:
        field = "date" if "日付" in str(e.detail) else "name"
        return templates.TemplateResponse(
            "components/partials/modals/custom_holiday_modal.html",
            {
                "request": request,
                "holiday": None,
                "modal_id": modal_id,
                "errors": {field: [e.detail]},
            },
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
    """祝日更新"""
    modal_id = f"edit-custom-holiday-{holiday_id}"
    try:
        updated = custom_holiday_service.update_custom_holiday_with_validation(
            db, custom_holiday_id=holiday_id, custom_holiday_in=holiday_in
        )
        return templates.TemplateResponse(
            "components/partials/modals/custom_holiday_modal.html",
            {"request": request, "holiday": updated, "modal_id": modal_id},
            headers={"HX-Trigger": json.dumps({"closeModal": modal_id, "refreshPage": True})},
        )
    except HTTPException as e:
        holiday = crud_custom_holiday.get(db, id=holiday_id)
        field = "date" if "日付" in str(e.detail) else "name"
        return templates.TemplateResponse(
            "components/partials/modals/custom_holiday_modal.html",
            {
                "request": request,
                "holiday": holiday,
                "modal_id": modal_id,
                "errors": {field: [e.detail]},
            },
        )


@router.delete("/{holiday_id}", response_class=HTMLResponse)
async def delete_custom_holiday(
    request: Request,
    holiday_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """祝日削除"""
    modal_id = f"custom-holiday-delete-modal-{holiday_id}"
    deleted = custom_holiday_service.delete_custom_holiday(db, custom_holiday_id=holiday_id)
    return templates.TemplateResponse(
        "components/partials/modals/custom_holiday_delete_modal.html",
        {"request": request, "holiday": deleted, "modal_id": modal_id},
        headers={"HX-Trigger": json.dumps({"closeModal": modal_id, "refreshPage": True})},
    )
