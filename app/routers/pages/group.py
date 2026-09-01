"""グループ管理ページエンドポイント。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import schemas
from app.crud.group import group
from app.db.session import get_db
from app.routers.pages.master_crud import MasterCrudResponder
from app.services import group_service
from app.services.errors import ApplicationError

router = APIRouter(prefix="/groups", tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")
responder = MasterCrudResponder(
    templates=templates,
    form_template="components/partials/modals/group_modal.html",
    delete_template="components/partials/modals/group_delete_modal.html",
)


@router.get("", response_class=HTMLResponse)
def group_manage_page(request: Request, db: Session = Depends(get_db)) -> Any:
    """グループ管理ページを表示する。"""
    return templates.TemplateResponse(
        "pages/group.html",
        {"request": request, "groups": group.get_multi(db)},
    )


@router.get("/modal", response_class=HTMLResponse)
@router.get("/modal/{group_id}", response_class=HTMLResponse)
async def group_modal(
    request: Request,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Any:
    """追加・編集モーダルを返す。"""
    group_data = group.get_or_404(db, group_id) if group_id is not None else None
    modal_id = "add-group" if group_id is None else f"edit-group-{group_id}"
    return responder.open_form(
        request,
        modal_id=modal_id,
        context={"group": group_data},
    )


@router.get("/delete-modal/{group_id}", response_class=HTMLResponse)
async def group_delete_modal(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """削除確認モーダルを返す。"""
    group_data = group.get_or_404(db, group_id)
    return responder.open_delete(
        request,
        modal_id=f"group-delete-modal-{group_id}",
        context={"group": group_data},
    )


@router.post("", response_class=HTMLResponse)
async def create_group(
    request: Request,
    group_in: schemas.GroupCreate = Depends(schemas.GroupCreate.as_form),
    db: Session = Depends(get_db),
) -> Any:
    """グループを作成し、標準master CRUD triggerを返す。"""
    modal_id = "add-group"
    try:
        created = group_service.create_group_with_validation(db=db, group_in=group_in)
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"group": created},
            message=f"グループ {created.name} を追加しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"group": None},
            errors={"name": [str(exc.detail)]},
        )


@router.put("/{group_id}", response_class=HTMLResponse)
async def update_group(
    request: Request,
    group_id: int,
    group_in: schemas.GroupUpdate = Depends(schemas.GroupUpdate.as_form),
    db: Session = Depends(get_db),
) -> Any:
    """グループを更新し、標準master CRUD triggerを返す。"""
    modal_id = f"edit-group-{group_id}"
    try:
        updated = group_service.update_group_with_validation(
            db=db,
            group_id=group_id,
            group_in=group_in,
        )
        return responder.form_success(
            request,
            modal_id=modal_id,
            context={"group": updated},
            message=f"グループ {updated.name} を更新しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context={"group": group.get(db, id=group_id)},
            errors={"name": [str(exc.detail)]},
        )


@router.delete("/{group_id}", response_class=HTMLResponse)
async def delete_group(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """グループを削除し、標準master CRUD triggerを返す。"""
    modal_id = f"group-delete-modal-{group_id}"
    group_data = group.get_or_404(db, group_id)
    group_name = str(group_data.name)
    try:
        group_service.delete_group(db=db, group_id=group_id)
        return responder.delete_success(
            modal_id=modal_id,
            message=f"グループ {group_name} を削除しました。",
        )
    except (HTTPException, ApplicationError) as exc:
        return responder.delete_error(
            request,
            modal_id=modal_id,
            context={"group": group.get(db, id=group_id)},
            warning_message=str(exc.detail),
        )
