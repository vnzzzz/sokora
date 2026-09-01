"""社員管理ページエンドポイント。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import schemas
from app.crud.group import group
from app.crud.user import user
from app.crud.user_type import user_type
from app.db.session import get_db
from app.routers.pages.master_crud import MasterCrudResponder
from app.services import master_read_service, user_service
from app.services.errors import ApplicationError

router = APIRouter(prefix="/users", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
responder = MasterCrudResponder(
    templates=templates,
    form_template="components/partials/modals/user_modal.html",
    delete_template="components/partials/modals/user_delete_modal.html",
)


def _user_form_context(db: Session, user_obj: Any) -> dict[str, Any]:
    return {
        "user": user_obj,
        "groups": group.get_multi(db),
        "user_types": user_type.get_multi(db),
    }


def _user_error_field(detail: str) -> str:
    if "ユーザーID" in detail:
        return "id"
    if "ユーザー名" in detail:
        return "username"
    if "グループ" in detail:
        return "group_id"
    if "社員種別" in detail:
        return "user_type_id"
    return "error"


@router.get("", response_class=HTMLResponse)
def user_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """社員管理ページを表示する。"""
    view = master_read_service.get_user_master_page_view_model(db)
    return templates.TemplateResponse(
        "pages/user.html",
        {
            "request": request,
            "users": view.users,
            "grouped_users": view.grouped_users,
            "group_names": view.group_names,
        },
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{user_id}", response_class=HTMLResponse)
async def user_modal(
    request: Request,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """追加・編集モーダルを返す。"""
    user_obj = user.get_or_404(db, user_id) if user_id is not None else None
    modal_id = f"user-modal-{user_id or 'new'}"
    return responder.open_form(
        request,
        modal_id=modal_id,
        context=_user_form_context(db, user_obj),
    )


@router.get("/delete-modal/{user_id}", response_class=HTMLResponse)
async def user_delete_modal(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """削除確認モーダルを返す。"""
    user_obj = user.get_or_404(db, user_id)
    return responder.open_delete(
        request,
        modal_id=f"user-delete-modal-{user_id}",
        context={"user": user_obj},
    )


@router.post("", response_class=HTMLResponse)
async def create_user(
    request: Request,
    user_in: schemas.UserCreate = Depends(schemas.UserCreate.as_form),
    db: Session = Depends(get_db),
) -> Any:
    """社員を作成し、標準master CRUD triggerを返す。"""
    modal_id = "user-modal-new"
    try:
        created = user_service.create_user_with_validation(db=db, user_in=user_in)
        return responder.form_success(
            request,
            modal_id=modal_id,
            context=_user_form_context(db, created),
            message=f"社員 {created.username} を追加しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        detail = str(exc.detail)
        return responder.form_error(
            request,
            modal_id=modal_id,
            context=_user_form_context(db, None),
            errors={_user_error_field(detail): [detail]},
        )


@router.put("/{user_id}", response_class=HTMLResponse)
async def update_user(
    request: Request,
    user_id: str,
    user_in: schemas.UserUpdate = Depends(schemas.UserUpdate.as_form),
    db: Session = Depends(get_db),
) -> Any:
    """社員を更新し、標準master CRUD triggerを返す。"""
    modal_id = f"user-modal-{user_id}"
    try:
        updated = user_service.update_user_with_validation(
            db=db,
            user_id=user_id,
            user_in=user_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context=_user_form_context(db, updated),
            message=f"社員 {updated.username} を更新しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        detail = str(exc.detail)
        return responder.form_error(
            request,
            modal_id=modal_id,
            context=_user_form_context(db, user.get(db, id=user_id)),
            errors={_user_error_field(detail): [detail]},
        )


@router.delete("/{user_id}", response_class=HTMLResponse)
async def delete_user(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """社員を削除し、標準master CRUD triggerを返す。"""
    modal_id = f"user-delete-modal-{user_id}"
    user_obj = user.get_or_404(db, user_id)
    username = str(user_obj.username)
    try:
        user_service.delete_user(db=db, user_id=user_id)
        return responder.delete_success(
            modal_id=modal_id,
            message=f"社員 {username} を削除しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.delete_error(
            request,
            modal_id=modal_id,
            context={"user": user.get(db, id=user_id)},
            warning_message=str(exc.detail),
        )
