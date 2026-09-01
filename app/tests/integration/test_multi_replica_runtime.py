"""Cross-process runtime consistency test against two live application replicas."""

import os
from datetime import date, timedelta
from uuid import uuid4

import httpx
import pytest

REPLICA_A_URL = os.getenv("SOKORA_REPLICA_A_URL")
REPLICA_B_URL = os.getenv("SOKORA_REPLICA_B_URL")

pytestmark = pytest.mark.skipif(
    not REPLICA_A_URL or not REPLICA_B_URL,
    reason="live replica URLs are not configured",
)


def _json_id(response: httpx.Response, expected_status: int = 200) -> int:
    assert response.status_code == expected_status, response.text
    return int(response.json()["id"])


def test_shared_postgresql_state_is_visible_across_replicas() -> None:
    assert REPLICA_A_URL is not None
    assert REPLICA_B_URL is not None

    suffix = uuid4().hex[:10]
    offset = int(suffix[:6], 16) % 3000
    holiday_date = date(2042, 1, 1) + timedelta(days=offset)
    holiday_name = f"Replica Holiday {suffix}"
    attendance_date = holiday_date

    with (
        httpx.Client(base_url=REPLICA_A_URL, timeout=10.0) as replica_a,
        httpx.Client(base_url=REPLICA_B_URL, timeout=10.0) as replica_b,
    ):
        holiday_write = replica_a.post(
            "/holidays",
            data={"date": holiday_date.isoformat(), "name": holiday_name},
        )
        assert holiday_write.status_code == 200, holiday_write.text

        calendar_read = replica_b.get(
            "/calendar",
            params={"month": holiday_date.strftime("%Y-%m")},
        )
        assert calendar_read.status_code == 200, calendar_read.text
        assert holiday_name in calendar_read.text

        group_id = _json_id(
            replica_a.post("/api/v1/groups", json={"name": f"replica-group-{suffix}"})
        )
        user_type_id = _json_id(
            replica_a.post(
                "/api/v1/user_types",
                json={"name": f"replica-user-type-{suffix}"},
            )
        )
        location_name = f"replica-location-{suffix}"
        location_id = _json_id(
            replica_a.post("/api/v1/locations", json={"name": location_name})
        )
        user_id = f"replica-user-{suffix}"
        user_name = f"Replica User {suffix}"
        user_write = replica_a.post(
            "/api/v1/users",
            json={
                "id": user_id,
                "username": user_name,
                "group_id": group_id,
                "user_type_id": user_type_id,
            },
        )
        assert user_write.status_code == 200, user_write.text

        attendance_write = replica_a.post(
            "/api/v1/attendances",
            json={
                "user_id": user_id,
                "date": attendance_date.isoformat(),
                "location_id": location_id,
                "note": f"replica-note-{suffix}",
            },
        )
        assert attendance_write.status_code == 201, attendance_write.text

        day_read = replica_b.get(f"/calendar/day/{attendance_date.isoformat()}")
        assert day_read.status_code == 200, day_read.text
        assert user_name in day_read.text
        assert location_name in day_read.text
