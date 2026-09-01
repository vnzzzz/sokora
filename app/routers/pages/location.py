"""勤怠種別管理ページエンドポイント。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import schemas
from app.crud.location import location
from app.db.session import get_db
from app.routers.pages.master_crud import MasterCrudResponder
from app.services import location_service, master_read_service
from app.services.errors import ApplicationError

router = APIRouter(prefix="/locations", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
responder = MasterCrudResponder(
    templates=templates,
    form_template="components/partials/modals/location_modal.html",
    delete_template="components/partials/modals/location_delete_modal.html",
)


@router.get("", response_class=HTMLResponse)
def get_location_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """勤怠種別管理ページを表示する。"""
    view = master_read_service.get_location_master_page_view_model(db)
    return templates.TemplateResponse(
        "pages/location.html",
        {
            "request": request,
            "locations": view.locations,
            "category_names": view.category_names,
            "grouped_locations": view.grouped_locations,
        },
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{location_id}", response_class=HTMLResponse)
async def location_modal(
    request: Request,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """追加・編集モーダルを返す。"""
    location_data = (
        location.get_or_404(db, location_id) if location_id is not None else None
    )
    modal_id = "add-location" if location_id is None else f"edit-location-{location_id}"
    return responder.open_form(
        request,
        modal_id=modal_id,
        context={"location": location_data},
    )


@router.get("/delete-modal/{location_id}", response_class=HTMLResponse)
async def location_delete_modal(
    request: Request,
    location_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """削除確認モーダルを返す。"""
    location_data = location.get_or_404(db, location_id)
    return responder.open_delete(
        request,
        modal_id=f"location-delete-modal-{location_id}",
        context={"location": location_data},
    )


@router.post("", response_class=HTMLResponse)
async def create_location(
    request: Request,
    location_in: schemas.location.LocationCreate = Depends(
        schemas.location.LocationCreate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """勤怠種別を作成し、標準master CRUD triggerを返す。"""
    modal_id = "add-location"
    try:
        created = location_service.create_location_with_validation(
            db=db,
            location_in=location_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"location": created},
            message=f"勤怠種別 {created.name} を追加しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"location": None},
            errors={"name": [str(exc.detail)]},
        )


@router.put("/{location_id}", response_class=HTMLResponse)
async def update_location(
    request: Request,
    location_id: int,
    location_in: schemas.location.LocationUpdate = Depends(
        schemas.location.LocationUpdate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """勤怠種別を更新し、標準master CRUD triggerを返す。"""
    modal_id = f"edit-location-{location_id}"
    try:
        updated = location_service.update_location_with_validation(
            db=db,
            location_id=location_id,
            location_in=location_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"location": updated},
            message=f"勤怠種別 {updated.name} を更新しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"location": location.get(db, id=location_id)},
            errors={"name": [str(exc.detail)]},
        )


@router.delete("/{location_id}", response_class=HTMLResponse)
async def delete_location(
    request: Request,
    location_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """勤怠種別を削除し、標準master CRUD triggerを返す。"""
    modal_id = f"location-delete-modal-{location_id}"
    location_data = location.get_or_404(db, location_id)
    location_name = str(location_data.name)
    try:
        location_service.delete_location(db=db, location_id=location_id)
        return responder.delete_success(
            modal_id=modal_id,
            message=f"勤怠種別 {location_name} を削除しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.delete_error(
            request,
            modal_id=modal_id,
            context={"location": location.get(db, id=location_id)},
            warning_message=str(exc.detail),
        )
