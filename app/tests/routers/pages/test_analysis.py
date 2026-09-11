"""Analysis page adapter contract tests."""

from datetime import date

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import models
from app.services import analysis_read_service

pytestmark = pytest.mark.asyncio


def _add_analysis_attendance(db: Session) -> None:
    group = db.query(models.Group).first()
    user_type = db.query(models.UserType).first()
    location = db.query(models.Location).first()
    assert group is not None and group.id is not None
    assert user_type is not None and user_type.id is not None
    assert location is not None and location.id is not None

    db.add(
        models.User(
            id="analysis-route-user",
            username="Analysis Route User",
            group_id=int(group.id),
            user_type_id=int(user_type.id),
        )
    )
    db.flush()
    db.add(
        models.Attendance(
            user_id="analysis-route-user",
            date=date(2031, 5, 3),
            location_id=int(location.id),
            note="route analysis",
        )
    )
    db.commit()


async def test_month_analysis_renders_read_model(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)
    location_count = db_with_data.query(models.Location).count()

    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_200_OK
    assert 'id="analysis-root"' in response.text
    assert "2031年5月" in response.text
    assert "Analysis Route User" in response.text
    assert 'data-testid="analysis-table"' in response.text
    assert 'data-testid="analysis-trend-chart"' in response.text
    assert f"集計対象 {location_count}件" in response.text


async def test_htmx_analysis_returns_fragment(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get(
        "/analysis?month=2031-05",
        headers={"HX-Request": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'id="analysis-view"' in response.text
    assert "<html" not in response.text


async def test_htmx_location_filter_returns_table_fragment_and_allows_zero_selection(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get(
        "/analysis?month=2031-05",
        headers={
            "HX-Request": "true",
            "HX-Target": "analysis-table-region",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'id="analysis-table-region"' in response.text
    assert 'id="analysis-view"' not in response.text
    assert "集計対象 0件" in response.text
    assert "集計対象を選択すると、グラフと社員別明細へ反映されます。" in response.text


async def test_htmx_history_restore_returns_full_page(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get(
        "/analysis?month=2031-05",
        headers={
            "HX-Request": "true",
            "HX-History-Restore-Request": "true",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert "<!DOCTYPE html>" in response.text
    assert 'id="analysis-view"' in response.text


async def test_fiscal_year_analysis_preserves_period_contract(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get("/analysis?mode=year&year=2031")

    assert response.status_code == status.HTTP_200_OK
    assert "2031年度" in response.text
    assert "4月〜翌3月" in response.text
    assert "Analysis Route User" in response.text
    assert "月別推移" in response.text


async def test_fiscal_year_outside_supported_range_is_422(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/analysis?mode=year&year=9999")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_fiscal_year_analysis_ignores_invalid_month_parameter(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get("/analysis?mode=year&year=2031&month=invalid")

    assert response.status_code == status.HTTP_200_OK
    assert "2031年度" in response.text


async def test_invalid_month_redirects_to_current_month(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.routers.pages.analysis.get_current_month_formatted",
        lambda: "2031-05",
    )

    response = await async_client.get(
        "/analysis?month=invalid",
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "/analysis?month=2031-05"


async def test_unexpected_analysis_failure_is_not_rendered_as_empty_200(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("unexpected analysis read failure")

    monkeypatch.setattr(
        analysis_read_service,
        "get_analysis_page_view_model",
        fail_read,
    )

    with pytest.raises(RuntimeError, match="unexpected analysis read failure"):
        await async_client.get("/analysis?month=2031-05")


async def test_database_unavailable_analysis_failure_returns_503_without_detail(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_read(*_args: object, **_kwargs: object) -> None:
        raise OperationalError(
            "SELECT users",
            {},
            RuntimeError("sensitive database unavailable detail"),
            connection_invalidated=True,
        )

    monkeypatch.setattr(
        analysis_read_service,
        "get_analysis_page_view_model",
        fail_read,
    )

    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "sensitive database unavailable detail" not in response.text


async def test_analysis_statement_error_returns_generic_500_without_detail(
    test_app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = OperationalError(
        "SELECT missing_table",
        {},
        RuntimeError("sensitive no such table detail"),
    )

    def fail_read(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(
        analysis_read_service,
        "get_analysis_page_view_model",
        fail_read,
    )

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "sensitive no such table detail" not in response.text
    assert "SELECT missing_table" not in response.text
