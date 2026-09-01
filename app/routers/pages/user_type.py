"""社員種別管理ページエンドポイント。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import schemas
from app.crud.user_type import user_type
from app.db.session import get_db
from app.routers.pages.master_crud import MasterCrudResponder
from app.services import user_type_service
from app.services.errors import ApplicationError

router = APIRouter(prefix="/user-types", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
responder = MasterCrudResponder(
    templates=templates,
    form_template="components/partials/modals/user_type_modal.html",
    delete_template="components/partials/modals/user_type_delete_modal.html",
)


@router.get("", response_class=HTMLResponse)
def get_user_type_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員種別管理ページを表示する。"""
    return templates.TemplateResponse(
        "pages/user_type.html",
        {"request": request, "user_types": user_type.get_multi(db)},
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{user_type_id}", response_class=HTMLResponse)
async def user_type_modal(
    request: Request,
    user_type_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """追加・編集モーダルを返す。"""
    user_type_data = (
        user_type.get_or_404(db, user_type_id) if user_type_id is not None else None
    )
    modal_id = (
        "add-user-type" if user_type_id is None else f"edit-user-type-{user_type_id}"
    )
    return responder.open_form(
        request,
        modal_id=modal_id,
        context={"user_type": user_type_data},
    )


@router.get("/delete-modal/{user_type_id}", response_class=HTMLResponse)
async def user_type_delete_modal(
    request: Request,
    user_type_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """削除確認モーダルを返す。"""
    user_type_data = user_type.get_or_404(db, user_type_id)
    return responder.open_delete(
        request,
        modal_id=f"user-type-delete-modal-{user_type_id}",
        context={"user_type": user_type_data},
    )


@router.post("", response_class=HTMLResponse)
async def create_user_type(
    request: Request,
    user_type_in: schemas.user_type.UserTypeCreate = Depends(
        schemas.user_type.UserTypeCreate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """社員種別を作成し、標準master CRUD triggerを返す。"""
    modal_id = "add-user-type"
    try:
        created = user_type_service.create_user_type_with_validation(
            db=db,
            user_type_in=user_type_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"user_type": created},
            message=f"社員種別 {created.name} を追加しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"user_type": None},
            errors={"name": [str(exc.detail)]},
        )


@router.put("/{user_type_id}", response_class=HTMLResponse)
async def update_user_type(
    request: Request,
    user_type_id: int,
    user_type_in: schemas.user_type.UserTypeUpdate = Depends(
        schemas.user_type.UserTypeUpdate.as_form
    ),
    db: Session = Depends(get_db),
) -> Any:
    """社員種別を更新し、標準master CRUD triggerを返す。"""
    modal_id = f"edit-user-type-{user_type_id}"
    try:
        updated = user_type_service.update_user_type_with_validation(
            db=db,
            user_type_id=user_type_id,
            user_type_in=user_type_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"user_type": updated},
            message=f"社員種別 {updated.name} を更新しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"user_type": user_type.get(db, id=user_type_id)},
            errors={"name": [str(exc.detail)]},
        )


@router.delete("/{user_type_id}", response_class=HTMLResponse)
async def delete_user_type(
    request: Request,
    user_type_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """社員種別を削除し、標準master CRUD triggerを返す。"""
    modal_id = f"user-type-delete-modal-{user_type_id}"
    user_type_data = user_type.get_or_404(db, user_type_id)
    user_type_name = str(user_type_data.name)
    try:
        user_type_service.delete_user_type(db=db, user_type_id=user_type_id)
        return responder.delete_success(
            modal_id=modal_id,
            message=f"社員種別 {user_type_name} を削除しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.delete_error(
            request,
            modal_id=modal_id,
            context={"user_type": user_type.get(db, id=user_type_id)},
            warning_message=str(exc.detail),
        )
