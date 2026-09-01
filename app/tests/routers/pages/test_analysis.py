"""Analysis page adapter contract tests."""

from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app import models

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

    response = await async_client.get("/analysis?month=2031-05")

    assert response.status_code == status.HTTP_200_OK
    assert 'id="analysis-root"' in response.text
    assert "2031年5月" in response.text
    assert "Analysis Route User" in response.text
    assert 'data-testid="analysis-table"' in response.text


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


async def test_invalid_month_renders_error_page(async_client: AsyncClient) -> None:
    response = await async_client.get("/analysis?month=invalid")

    assert response.status_code == status.HTTP_200_OK
    assert "エラー" in response.text
    assert "Internal Server Error" not in response.text
