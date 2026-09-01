"""Calendar page adapter contract tests."""

from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app import crud, models, schemas

pytestmark = pytest.mark.asyncio


def _references(db: Session) -> tuple[models.Group, models.UserType, models.Location]:
    group = db.query(models.Group).first()
    user_type = db.query(models.UserType).first()
    location = db.query(models.Location).first()
    assert group is not None and group.id is not None
    assert user_type is not None and user_type.id is not None
    assert location is not None and location.id is not None
    return group, user_type, location


async def test_month_calendar_preserves_htmx_fragment_contract(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(
        "/calendar?month=2031-05",
        headers={"HX-Request": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["HX-Reswap"] == "innerHTML"
    assert 'id="calendar-metadata"' in response.text
    assert "2031-05" in response.text


async def test_day_detail_renders_grouped_attendance(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    db = db_with_data
    group, user_type, location = _references(db)
    user_id = "calendar-route-user"
    target_date = date(2031, 7, 3)

    crud.user.create(
        db,
        obj_in=schemas.UserCreate(
            id=user_id,
            username="Calendar Route User",
            group_id=int(group.id),
            user_type_id=int(user_type.id),
        ),
    )
    crud.attendance.create(
        db,
        obj_in=schemas.AttendanceCreate(
            user_id=user_id,
            date=target_date,
            location_id=int(location.id),
            note="route note",
        ),
    )
    db.commit()

    response = await async_client.get(f"/calendar/day/{target_date.isoformat()}")

    assert response.status_code == status.HTTP_200_OK
    assert f"{target_date.isoformat()}の勤怠情報" in response.text
    assert "Calendar Route User" in response.text
    assert str(group.name) in response.text
    assert str(location.name) in response.text
    assert "route note" in response.text


async def test_invalid_day_returns_empty_detail(async_client: AsyncClient) -> None:
    response = await async_client.get("/calendar/day/not-a-date")

    assert response.status_code == status.HTTP_200_OK
    assert "not-a-dateの勤怠情報" in response.text
    assert "記録なし" in response.text
