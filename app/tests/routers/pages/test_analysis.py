"""Analysis page adapter contract tests."""

from datetime import date

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import models
from app.services import analysis_coverage_service, analysis_read_service

pytestmark = pytest.mark.asyncio


def _add_analysis_attendance(db: Session) -> tuple[models.Group, models.UserType]:
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
    return group, user_type


async def test_month_analysis_renders_one_chart_and_target_filters_by_default(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_200_OK
    assert 'id="analysis-root"' in response.text
    assert 'id="month-input"' in response.text
    assert 'value="2031-05"' in response.text
    assert 'id="analysis-group-select"' in response.text
    assert 'id="analysis-user-type-select"' in response.text
    assert 'data-testid="analysis-coverage-chart"' in response.text
    assert response.text.count('data-testid="analysis-chart-scroller"') == 1
    assert 'data-testid="analysis-chart-target"' in response.text
    assert "全グループ / 全社員種別" in response.text
    assert 'id="analysis-total-series"' in response.text
    assert 'name="show_total"' in response.text
    assert "全合計" in response.text
    assert "勤怠種別" in response.text
    assert 'data-analysis-day="2031-05-03"' in response.text
    assert 'id="analysis-day-detail"' in response.text
    assert 'data-testid="analysis-table"' not in response.text
    assert 'data-testid="analysis-trend-chart"' not in response.text


async def test_analysis_without_any_users_preserves_period_empty_message(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    """勤怠種別は存在するがuserが1人も登録されていない場合、全合計0の chartではなく
    period-specific empty_messageを表示する。group_sectionsが空でも全合計seriesは
    常時描画できてしまうため、chart側でこのcaseを明示的に区別する必要がある。
    """
    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_200_OK
    assert 'data-testid="analysis-empty-message"' in response.text
    assert "2031年5月の勤怠データがありません。" in response.text
    assert 'data-testid="analysis-coverage-chart"' not in response.text


async def test_target_filters_render_selected_intersection(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    group, user_type = _add_analysis_attendance(db_with_data)

    response = await async_client.get(
        "/analysis",
        params={
            "month": "2031-05",
            "group_name": group.name,
            "user_type_name": user_type.name,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert f'value="{group.name}" selected' in response.text
    assert f'value="{user_type.name}" selected' in response.text
    assert f"{group.name} / {user_type.name}" in response.text
    assert response.text.count('data-testid="analysis-chart-scroller"') == 1


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


async def test_htmx_filter_can_clear_all_series(
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
    assert 'data-testid="analysis-no-selection-hint"' in response.text
    assert "勤怠種別を選択してください。" in response.text
    assert 'data-testid="analysis-coverage-chart"' not in response.text


async def test_htmx_filter_preserves_target_while_rendering_total(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    group, user_type = _add_analysis_attendance(db_with_data)

    response = await async_client.get(
        "/analysis",
        params={
            "month": "2031-05",
            "show_total": "true",
            "group_name": group.name,
            "user_type_name": user_type.name,
        },
        headers={
            "HX-Request": "true",
            "HX-Target": "analysis-table-region",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert 'data-testid="analysis-coverage-chart"' in response.text
    assert f"{group.name} / {user_type.name}" in response.text
    assert "全合計" in response.text
    assert 'data-testid="analysis-no-selection-hint"' not in response.text


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


async def test_more_than_ten_series_are_split_into_chart_panels(
    async_client: AsyncClient,
    db_with_data: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1chartに11個以上のseriesが乗ると、色toneと点線patternの両方が
    location_id基準で10周期になり、11番目以降が1番目以降と完全に同一の
    見た目になってしまう。panelを10 series単位で分割し、pattern/tone衝突が
    同一panel内で起きないようにする。
    """
    _add_analysis_attendance(db_with_data)
    points = [
        {"key": "2031-05-01", "label": "1", "count": 0},
        {"key": "2031-05-02", "label": "2", "count": 0},
    ]
    series = [
        {
            "location_id": index,
            "name": f"Work Type {index}",
            "tone_index": index % 10,
            "is_total": False,
            "points": points,
        }
        for index in range(1, 12)
    ]

    monkeypatch.setattr(
        analysis_coverage_service,
        "get_analysis_coverage_view_model",
        lambda **_kwargs: {
            "include_total": True,
            "coverage_locations": [],
            "coverage_buckets": [
                ("2031-05-01", "1"),
                ("2031-05-02", "2"),
            ],
            "group_options": [],
            "user_type_options": [],
            "selected_group_name": None,
            "selected_user_type_name": None,
            "coverage_chart": {
                "label": "全グループ / 全社員種別",
                "max_count": 1,
                "series": series,
            },
        },
    )

    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_200_OK
    assert response.text.count('data-testid="analysis-chart-panel"') == 2
    assert response.text.count('data-testid="analysis-chart-scroller"') == 2
    assert "Work Type 1" in response.text
    assert "Work Type 11" in response.text


async def test_fiscal_year_analysis_preserves_period_contract(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    _add_analysis_attendance(db_with_data)

    response = await async_client.get("/analysis?mode=year&year=2031")

    assert response.status_code == status.HTTP_200_OK
    assert 'id="year-select"' in response.text
    assert 'value="2031" selected' in response.text
    assert 'data-testid="analysis-coverage-chart"' in response.text
    assert response.text.count('data-testid="analysis-chart-scroller"') == 1
    assert "data-analysis-day=" not in response.text
    assert 'id="analysis-day-detail"' not in response.text


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
