"""Read failure / attendance read-model regression contracts."""

from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import crud, schemas
from app.crud.calendar import calendar_crud
from app.services import analysis_read_service

pytestmark = pytest.mark.asyncio


def _create_users(db: Session, count: int) -> None:
    group = crud.group.list_all(db)[0]
    user_type = crud.user_type.list_all(db)[0]
    assert group.id is not None
    assert user_type.id is not None

    for index in range(count):
        crud.user.create(
            db,
            obj_in=schemas.UserCreate(
                id=f"read-model-{index}",
                username=f"Read Model {index}",
                group_id=int(group.id),
                user_type_id=int(user_type.id),
            ),
        )
    db.commit()
    db.expire_all()


async def _count_selects(
    db: Session,
    request: Callable[[], object],
) -> tuple[int, object]:
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
        response = await request()  # type: ignore[misc]
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    return select_count, response


async def test_weekly_read_query_count_does_not_scale_per_user(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _create_users(db_with_data, 4)

    select_count, response = await _count_selects(
        db_with_data,
        lambda: async_client.get("/attendance/weekly?week=2031-05-12"),
    )

    assert response.status_code == 200  # type: ignore[attr-defined]
    assert select_count <= 5


async def test_monthly_user_list_query_count_does_not_scale_per_user(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _create_users(db_with_data, 4)

    select_count, response = await _count_selects(
        db_with_data,
        lambda: async_client.get("/attendance/monthly?month=2031-05"),
    )

    assert response.status_code == 200  # type: ignore[attr-defined]
    assert select_count <= 4


async def test_weekly_unexpected_failure_is_not_normalized_to_200(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args, **_kwargs):
        raise RuntimeError("programming failure")

    monkeypatch.setattr(calendar_crud, "get_week_attendances", fail_read)

    with pytest.raises(RuntimeError, match="programming failure"):
        await async_client.get("/attendance/weekly?week=2031-05-12")


async def test_weekly_database_operational_failure_is_503_without_details(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args, **_kwargs):
        raise OperationalError("SELECT db-secret", {}, Exception("db-secret"))

    monkeypatch.setattr(calendar_crud, "get_week_attendances", fail_read)

    response = await async_client.get("/attendance/weekly?week=2031-05-12")

    assert response.status_code == 503
    assert "db-secret" not in response.text


async def test_monthly_user_calendar_invalid_month_is_explicit_400(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _create_users(db_with_data, 1)

    response = await async_client.get(
        "/attendance/monthly/users/read-model-0?month=invalid"
    )

    assert response.status_code == 400


async def test_calendar_invalid_month_is_explicit_400(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/calendar?month=invalid")

    assert response.status_code == 400
    assert "エラー" in response.text


async def test_analysis_invalid_month_is_explicit_400(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/analysis?month=invalid")

    assert response.status_code == 400
    assert "エラー" in response.text


async def test_analysis_unexpected_failure_is_not_normalized_to_200(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args, **_kwargs):
        raise RuntimeError("analysis programming failure")

    monkeypatch.setattr(
        analysis_read_service,
        "get_analysis_page_view_model",
        fail_read,
    )

    with pytest.raises(RuntimeError, match="analysis programming failure"):
        await async_client.get("/analysis?month=2031-05")


async def test_analysis_database_operational_failure_is_503_without_details(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args, **_kwargs):
        raise OperationalError("SELECT analysis-secret", {}, Exception("analysis-secret"))

    monkeypatch.setattr(
        analysis_read_service,
        "get_analysis_page_view_model",
        fail_read,
    )

    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == 503
    assert "analysis-secret" not in response.text
