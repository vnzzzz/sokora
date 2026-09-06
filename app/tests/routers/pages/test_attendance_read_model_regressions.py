"""Attendance weekly/monthly read-model regression contracts."""

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app import crud, schemas
from app.crud.calendar import calendar_crud


def _base_ids(db: Session) -> tuple[int, int]:
    group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="Read Model Group"),
    )
    user_type = crud.user_type.create(
        db,
        obj_in=schemas.UserTypeCreate(name="Read Model Type"),
    )
    crud.location.create(
        db,
        obj_in=schemas.LocationCreate(name="Read Model Location"),
    )
    db.commit()
    assert group.id is not None
    assert user_type.id is not None
    return int(group.id), int(user_type.id)


def _create_users(db: Session, *, count: int) -> None:
    group_id, user_type_id = _base_ids(db)
    for index in range(count):
        crud.user.create(
            db,
            obj_in=schemas.UserCreate(
                id=f"read-model-user-{index}",
                username=f"Read Model User {index}",
                group_id=group_id,
                user_type_id=user_type_id,
            ),
        )
    db.commit()
    db.expire_all()


async def _count_route_selects(
    async_client: AsyncClient,
    db: Session,
    url: str,
) -> tuple[int, int]:
    select_count = 0

    def count_selects(
        _conn,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        response = await async_client.get(url)
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    return response.status_code, select_count


@pytest.mark.asyncio
async def test_weekly_read_query_count_does_not_scale_with_users(
    async_client: AsyncClient,
    db: Session,
) -> None:
    _create_users(db, count=8)

    status_code, select_count = await _count_route_selects(
        async_client,
        db,
        "/attendance/weekly?week=2031-05-12",
    )

    assert status_code == 200
    assert select_count <= 8


@pytest.mark.asyncio
async def test_monthly_read_query_count_does_not_scale_with_users(
    async_client: AsyncClient,
    db: Session,
) -> None:
    _create_users(db, count=8)

    status_code, select_count = await _count_route_selects(
        async_client,
        db,
        "/attendance/monthly?month=2031-05",
    )

    assert status_code == 200
    assert select_count <= 8


@pytest.mark.asyncio
async def test_weekly_outside_supported_year_redirects_to_current_week(
    test_app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.routers.pages.attendance.get_current_week_formatted",
        lambda: "2031-05-12",
    )

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/attendance/weekly?week=9999-12-27",
            follow_redirects=False,
        )

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "/attendance/weekly?week=2031-05-12"


@pytest.mark.asyncio
async def test_weekly_unexpected_read_failure_is_not_rendered_as_empty_200(
    async_client: AsyncClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args, **_kwargs):
        raise RuntimeError("unexpected weekly read failure")

    monkeypatch.setattr(calendar_crud, "get_week_attendances", fail_read)

    with pytest.raises(RuntimeError, match="unexpected weekly read failure"):
        await async_client.get("/attendance/weekly?week=2031-05-12")


@pytest.mark.asyncio
async def test_user_monthly_unexpected_read_failure_is_not_rendered_as_empty_200(
    async_client: AsyncClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_users(db, count=1)

    def fail_read(*_args, **_kwargs):
        raise RuntimeError("unexpected monthly read failure")

    monkeypatch.setattr(crud.attendance, "list_user_for_period", fail_read)

    with pytest.raises(RuntimeError, match="unexpected monthly read failure"):
        await async_client.get(
            "/attendance/monthly/users/read-model-user-0?month=2031-05"
        )
