"""Administrator-only SQLite database management pages."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.db.session import (
    DatabaseRuntime,
    get_app_database_runtime,
    sqlalchemy_database_url,
    sqlite_database_path,
)
from app.services.auth.dependencies import require_admin
from app.services.database_management import (
    DatabaseManagementError,
    create_sqlite_backup,
    restore_sqlite_database,
    stage_sqlite_restore_upload,
)

router = APIRouter(prefix="/admin/database", tags=["Database"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def _actor_name(admin: dict[str, object]) -> str:
    return str(admin.get("username") or admin.get("subject") or "unknown")


def _page_context(
    request: Request,
    runtime: DatabaseRuntime,
    *,
    restored: bool = False,
    error_message: str | None = None,
) -> dict[str, object]:
    database_path = sqlite_database_path(runtime.database_url)
    backend = sqlalchemy_database_url(runtime.database_url).get_backend_name()
    return {
        "request": request,
        "backend": backend,
        "sqlite_available": database_path is not None,
        "database_filename": database_path.name if database_path is not None else None,
        "restored": restored,
        "error_message": error_message,
    }


def _delete_temporary_file(path: Path) -> None:
    path.unlink(missing_ok=True)


@router.get("", response_class=HTMLResponse)
async def database_management_page(
    request: Request,
    result: str | None = None,
    _admin: dict[str, object] = Depends(require_admin),
) -> Response:
    runtime = get_app_database_runtime(request.app)
    return templates.TemplateResponse(
        "pages/admin/database.html",
        _page_context(request, runtime, restored=result == "restored"),
    )


@router.get("/backup")
async def download_database_backup(
    request: Request,
    admin: dict[str, object] = Depends(require_admin),
) -> Response:
    runtime = get_app_database_runtime(request.app)
    actor = _actor_name(admin)

    try:
        backup_path = await run_in_threadpool(create_sqlite_backup, runtime)
    except DatabaseManagementError as exc:
        logger.warning("SQLite backup rejected actor=%s reason=%s", actor, exc.detail)
        return templates.TemplateResponse(
            "pages/admin/database.html",
            _page_context(request, runtime, error_message=exc.detail),
            status_code=exc.status_code,
        )

    logger.info("SQLite backup created actor=%s", actor)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return FileResponse(
        path=backup_path,
        filename=f"sokora-backup-{timestamp}.db",
        media_type="application/vnd.sqlite3",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(_delete_temporary_file, backup_path),
    )


@router.post("/restore")
async def restore_database_backup(
    request: Request,
    database: UploadFile = File(...),
    confirm_restore: str = Form(""),
    admin: dict[str, object] = Depends(require_admin),
) -> Response:
    runtime = get_app_database_runtime(request.app)
    actor = _actor_name(admin)
    staged_path: Path | None = None

    if confirm_restore != "yes":
        await database.close()
        return templates.TemplateResponse(
            "pages/admin/database.html",
            _page_context(
                request,
                runtime,
                error_message="リストア確認が必要です。",
            ),
            status_code=400,
        )

    try:
        staged_path = await run_in_threadpool(
            stage_sqlite_restore_upload,
            database.file,
            runtime,
        )
        await run_in_threadpool(restore_sqlite_database, runtime, staged_path)
    except DatabaseManagementError as exc:
        logger.warning(
            "SQLite restore rejected actor=%s filename=%s reason=%s",
            actor,
            database.filename,
            exc.detail,
        )
        return templates.TemplateResponse(
            "pages/admin/database.html",
            _page_context(request, runtime, error_message=exc.detail),
            status_code=exc.status_code,
        )
    finally:
        await database.close()
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)

    logger.info(
        "SQLite restore completed actor=%s filename=%s",
        actor,
        database.filename,
    )
    return RedirectResponse(
        "/admin/database?result=restored",
        status_code=303,
    )
