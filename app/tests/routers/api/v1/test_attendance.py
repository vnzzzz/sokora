"""Attendance JSON API contract tests."""

from datetime import date

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def create_test_group_via_api(async_client: AsyncClient, name: str) -> int:
    response = await async_client.post("/api/v1/groups", json={"name": name})
    assert response.status_code == status.HTTP_200_OK
    return int(response.json()["id"])


async def create_test_user_type_via_api(async_client: AsyncClient, name: str) -> int:
    response = await async_client.post("/api/v1/user_types", json={"name": name})
    assert response.status_code == status.HTTP_200_OK
    return int(response.json()["id"])


async def create_test_location_via_api(async_client: AsyncClient, name: str) -> int:
    response = await async_client.post("/api/v1/locations", json={"name": name})
    assert response.status_code == status.HTTP_200_OK
    return int(response.json()["id"])


async def create_test_user_via_api(
    async_client: AsyncClient,
    user_id: str,
    username: str,
    group_id: int,
    user_type_id: int,
) -> str:
    response = await async_client.post(
        "/api/v1/users",
        json={
            "id": user_id,
            "username": username,
            "group_id": group_id,
            "user_type_id": user_type_id,
        },
    )
    assert response.status_code in {
        status.HTTP_200_OK,
        status.HTTP_201_CREATED,
        status.HTTP_204_NO_CONTENT,
    }
    return user_id


async def _attendance_references(
    async_client: AsyncClient, suffix: str
) -> tuple[str, int]:
    group_id = await create_test_group_via_api(async_client, f"Group {suffix}")
    user_type_id = await create_test_user_type_via_api(
        async_client, f"User Type {suffix}"
    )
    user_id = await create_test_user_via_api(
        async_client,
        f"user-{suffix}",
        f"User {suffix}",
        group_id,
        user_type_id,
    )
    location_id = await create_test_location_via_api(
        async_client, f"Location {suffix}"
    )
    return user_id, location_id


async def test_attendance_json_api_crud(async_client: AsyncClient) -> None:
    user_id, first_location_id = await _attendance_references(async_client, "json")
    second_location_id = await create_test_location_via_api(
        async_client, "Location json updated"
    )
    attendance_date = date(2030, 1, 15)

    create_response = await async_client.post(
        "/api/v1/attendances",
        json={
            "user_id": user_id,
            "date": attendance_date.isoformat(),
            "location_id": first_location_id,
            "note": "created",
        },
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    assert "HX-Trigger" not in create_response.headers
    created = create_response.json()
    assert created["user_id"] == user_id
    assert created["date"] == attendance_date.isoformat()
    assert created["location_id"] == first_location_id
    attendance_id = int(created["id"])

    list_response = await async_client.get("/api/v1/attendances")
    assert list_response.status_code == status.HTTP_200_OK
    assert any(
        record["id"] == attendance_id for record in list_response.json()["records"]
    )

    update_response = await async_client.put(
        f"/api/v1/attendances/{attendance_id}",
        json={"location_id": second_location_id, "note": "updated"},
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert "HX-Trigger" not in update_response.headers
    assert update_response.json()["location_id"] == second_location_id
    assert update_response.json()["note"] == "updated"

    delete_response = await async_client.delete(f"/api/v1/attendances/{attendance_id}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert "HX-Trigger" not in delete_response.headers


async def test_attendance_json_api_duplicate_is_400(async_client: AsyncClient) -> None:
    user_id, location_id = await _attendance_references(async_client, "duplicate")
    payload = {
        "user_id": user_id,
        "date": "2030-02-01",
        "location_id": location_id,
    }
    first = await async_client.post("/api/v1/attendances", json=payload)
    second = await async_client.post("/api/v1/attendances", json=payload)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に勤怠データが存在します" in second.json()["detail"]


async def test_attendance_json_api_not_found_and_validation(
    async_client: AsyncClient,
) -> None:
    location_id = await create_test_location_via_api(
        async_client, "Location invalid user"
    )
    not_found = await async_client.post(
        "/api/v1/attendances",
        json={
            "user_id": "missing-user",
            "date": "2030-03-01",
            "location_id": location_id,
        },
    )
    invalid_date = await async_client.post(
        "/api/v1/attendances",
        json={
            "user_id": "missing-user",
            "date": "2030-13-01",
            "location_id": location_id,
        },
    )

    assert not_found.status_code == status.HTTP_404_NOT_FOUND
    assert not_found.json() == {"detail": "User with id missing-user not found"}
    assert invalid_date.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_get_day_attendance_projection(async_client: AsyncClient) -> None:
    user_id, location_id = await _attendance_references(async_client, "day")
    attendance_date = date(2030, 4, 2)
    await async_client.post(
        "/api/v1/attendances",
        json={
            "user_id": user_id,
            "date": attendance_date.isoformat(),
            "location_id": location_id,
            "note": "day note",
        },
    )

    response = await async_client.get(
        f"/api/v1/attendances/day/{attendance_date.isoformat()}"
    )
    assert response.status_code == status.HTTP_200_OK
    values = list(response.json()["data"].values())
    assert values and values[0][0]["user_id"] == user_id
    assert values[0][0]["note"] == "day note"
