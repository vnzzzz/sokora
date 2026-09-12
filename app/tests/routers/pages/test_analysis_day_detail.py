"""Analysis day-detail filter contract tests."""

from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app import models

pytestmark = pytest.mark.asyncio


def _add_filtered_day_fixture(db: Session) -> dict[str, object]:
    group_a = models.Group(name="Analysis Detail Group A", order=10)
    group_b = models.Group(name="Analysis Detail Group B", order=20)
    type_a = models.UserType(name="Analysis Detail Type A", order=10)
    type_b = models.UserType(name="Analysis Detail Type B", order=20)
    location_a = models.Location(name="Analysis Detail Office A", category="勤務", order=10)
    location_b = models.Location(name="Analysis Detail Office B", category="勤務", order=20)
    db.add_all([group_a, group_b, type_a, type_b, location_a, location_b])
    db.flush()

    fixtures = [
        ("detail-match", "Detail Match", group_a, type_a, location_a),
        ("detail-location", "Detail Other Location", group_a, type_a, location_b),
        ("detail-group", "Detail Other Group", group_b, type_a, location_a),
        ("detail-type", "Detail Other Type", group_a, type_b, location_a),
    ]
    target_date = date(2031, 5, 3)
    for user_id, username, group, user_type, location in fixtures:
        db.add(
            models.User(
                id=user_id,
                username=username,
                group_id=group.id,
                user_type_id=user_type.id,
            )
        )
        db.flush()
        db.add(
            models.Attendance(
                user_id=user_id,
                date=target_date,
                location_id=location.id,
            )
        )
    db.commit()

    return {
        "group": group_a,
        "user_type": type_a,
        "location": location_a,
        "date": target_date,
    }


async def test_analysis_day_detail_applies_all_active_filters(
    async_client: AsyncClient,
    db_with_data: Session,
) -> None:
    fixture = _add_filtered_day_fixture(db_with_data)
    group = fixture["group"]
    user_type = fixture["user_type"]
    location = fixture["location"]
    target_date = fixture["date"]
    assert isinstance(group, models.Group)
    assert isinstance(user_type, models.UserType)
    assert isinstance(location, models.Location)
    assert isinstance(target_date, date)
    assert location.id is not None

    response = await async_client.get(
        f"/analysis/day/{target_date.isoformat()}",
        params={
            "group_name": group.name,
            "user_type_name": user_type.name,
            "selected_locations": int(location.id),
        },
        headers={"HX-Request": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "Detail Match" in response.text
    assert "Analysis Detail Office A" in response.text
    assert "Detail Other Location" not in response.text
    assert "Detail Other Group" not in response.text
    assert "Detail Other Type" not in response.text
    assert "Analysis Detail Office B" not in response.text
