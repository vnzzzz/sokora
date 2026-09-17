"""社員管理ページエンドポイント。"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
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
    """社員formに必要なmaster dataをまとめる。

    Args:
        db: 参照に使うDB session。
        user_obj: 編集対象社員。新規作成時は ``None``。

    Returns:
        form templateへ渡す社員・group・社員種別のcontext。
    """
    return {
        "user": user_obj,
        "groups": group.list_all(db),
        "user_types": user_type.list_all(db),
    }


def _user_error_field(detail: str) -> str:
    """domain error messageを社員formのfield keyへ対応付ける。

    Args:
        detail: service/HTTPExceptionから得た表示用error detail。

    Returns:
        form validation errorを表示するfield key。
    """
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
    """社員管理ページを表示する。

    Args:
        request: 現在のHTTP request。
        db: read model構築に使うDB session。

    Returns:
        社員master pageのHTML response。
    """
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
    """社員の追加・編集モーダルを返す。

    Args:
        request: 現在のHTTP request。
        user_id: 編集対象社員ID。省略時は新規作成。
        db: master data取得に使うDB session。

    Returns:
        modal fragmentのHTML response。

    Raises:
        HTTPException: 指定社員が存在しない場合。
    """
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
    """社員削除の確認モーダルを返す。

    Args:
        request: 現在のHTTP request。
        user_id: 削除対象社員ID。
        db: 対象取得に使うDB session。

    Returns:
        delete modal fragmentのHTML response。

    Raises:
        HTTPException: 指定社員が存在しない場合。
    """
    user_obj = user.get_or_404(db, user_id)
    return responder.open_delete(
        request,
        modal_id=f"user-delete-modal-{user_id}",
        context={"user": user_obj},
    )


@router.post("", response_class=HTMLResponse)
async def create_user(
    request: Request,
    id: str = Form(...),
    username: str = Form(...),
    group_id: str = Form(...),
    user_type_id: str = Form(...),
    db: Session = Depends(get_db),
) -> Any:
    """社員を作成し、標準master CRUD triggerを返す。

    Args:
        request: 現在のHTTP request。
        id: 新規社員ID。
        username: 新規社員名。
        group_id: 所属group IDのform値。
        user_type_id: 社員種別IDのform値。
        db: write transactionに使うDB session。

    Returns:
        成功時はrefresh trigger付きresponse、validation failure時はform error fragment。
    """
    modal_id = "user-modal-new"
    try:
        user_in = schemas.UserCreate(
            id=id,
            username=username,
            group_id=group_id,
            user_type_id=user_type_id,
        )
        created = user_service.create_user_with_validation(db=db, user_in=user_in)
        return responder.form_success(
            request,
            modal_id=modal_id,
            context=_user_form_context(db, created),
            message=f"社員 {created.username} を追加しました。",
        )
    except ValidationError:
        return responder.form_error(
            request,
            modal_id=modal_id,
            context=_user_form_context(db, None),
            errors={"id": ["ユーザーIDは半角英数、-、_のみ使用できます。"]},
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
    """社員を更新し、標準master CRUD triggerを返す。

    Args:
        request: 現在のHTTP request。
        user_id: 更新対象社員ID。
        user_in: formから構築した更新payload。
        db: write transactionに使うDB session。

    Returns:
        成功時はrefresh trigger付きresponse、domain error時はform error fragment。
    """
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
    """社員を削除し、標準master CRUD triggerを返す。

    Args:
        request: 現在のHTTP request。
        user_id: 削除対象社員ID。
        db: write transactionに使うDB session。

    Returns:
        成功時はrefresh trigger付きresponse、削除拒否時はdelete modal error fragment。

    Raises:
        HTTPException: 削除対象社員が存在しない場合。
    """
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
