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
    """勤怠種別管理ページを表示する。

    Args:
        request: 現在のHTTP request。
        db: read model構築に使うDB session。

    Returns:
        勤怠種別master pageのHTML response。
    """
    view = master_read_service.get_location_master_page_view_model(db)
    return templates.TemplateResponse(
        "pages/location.html",
        {
            "request": request,
            "locations": view.locations,
            "category_names": view.category_names,
            "grouped_locations": view.grouped_locations,
            "location_tones": view.location_tones,
        },
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{location_id}", response_class=HTMLResponse)
async def location_modal(
    request: Request,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """勤怠種別の追加・編集モーダルを返す。

    Args:
        request: 現在のHTTP request。
        location_id: 編集対象ID。省略時は新規作成。
        db: 対象取得に使うDB session。

    Returns:
        modal fragmentのHTML response。

    Raises:
        HTTPException: 指定した勤怠種別が存在しない場合。
    """
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
    """勤怠種別削除の確認モーダルを返す。

    Args:
        request: 現在のHTTP request。
        location_id: 削除対象ID。
        db: 対象取得に使うDB session。

    Returns:
        delete modal fragmentのHTML response。

    Raises:
        HTTPException: 指定した勤怠種別が存在しない場合。
    """
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
    """勤怠種別を作成し、標準master CRUD triggerを返す。

    Args:
        request: 現在のHTTP request。
        location_in: formから構築した作成payload。
        db: write transactionに使うDB session。

    Returns:
        成功時はrefresh trigger付きresponse、domain error時はform error fragment。
    """
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
    """勤怠種別を更新し、標準master CRUD triggerを返す。

    Args:
        request: 現在のHTTP request。
        location_id: 更新対象ID。
        location_in: formから構築した更新payload。
        db: write transactionに使うDB session。

    Returns:
        成功時はrefresh trigger付きresponse、domain error時はform error fragment。
    """
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
    """勤怠種別を削除し、標準master CRUD triggerを返す。

    Args:
        request: 現在のHTTP request。
        location_id: 削除対象ID。
        db: write transactionに使うDB session。

    Returns:
        成功時はrefresh trigger付きresponse、削除拒否時はdelete modal error fragment。

    Raises:
        HTTPException: 削除対象が存在しない場合。
    """
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
