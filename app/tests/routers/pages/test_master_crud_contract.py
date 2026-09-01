"""Shared interaction contracts for master-management SSR/HTMX routes."""

import json

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.orm import Session

from app import crud, models, schemas

pytestmark = pytest.mark.asyncio


def _trigger(response: Response) -> dict[str, object]:
    assert response.status_code == 200, response.text
    return json.loads(response.headers["HX-Trigger"])


def _assert_open_modal(response: Response, modal_id: str) -> None:
    assert _trigger(response) == {"openModal": modal_id}


def _assert_mutation_success(response: Response, modal_id: str) -> None:
    trigger = _trigger(response)
    assert trigger["closeModal"] == modal_id
    assert trigger["refreshPage"] is True
    assert isinstance(trigger["showMessage"], str)
    assert trigger["showMessage"]


def _assert_inline_error(response: Response) -> None:
    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers
    assert "text-error text-sm" in response.text


async def test_group_master_crud_uses_standard_modal_contract(
    async_client: AsyncClient,
    db: Session,
) -> None:
    _assert_open_modal(await async_client.get("/groups/modal"), "add-group")

    created_response = await async_client.post(
        "/groups",
        data={"name": "master-contract-group", "order": "10"},
    )
    _assert_mutation_success(created_response, "add-group")
    created = (
        db.query(models.Group).filter(models.Group.name == "master-contract-group").one()
    )

    duplicate_response = await async_client.post(
        "/groups",
        data={"name": "master-contract-group", "order": "20"},
    )
    _assert_inline_error(duplicate_response)

    _assert_open_modal(
        await async_client.get(f"/groups/modal/{created.id}"),
        f"edit-group-{created.id}",
    )
    updated_response = await async_client.put(
        f"/groups/{created.id}",
        data={"name": "master-contract-group-updated", "order": "11"},
    )
    _assert_mutation_success(updated_response, f"edit-group-{created.id}")

    _assert_open_modal(
        await async_client.get(f"/groups/delete-modal/{created.id}"),
        f"group-delete-modal-{created.id}",
    )
    deleted_response = await async_client.delete(f"/groups/{created.id}")
    _assert_mutation_success(deleted_response, f"group-delete-modal-{created.id}")
    assert db.get(models.Group, created.id) is None


async def test_location_master_crud_uses_standard_modal_contract(
    async_client: AsyncClient,
    db: Session,
) -> None:
    _assert_open_modal(await async_client.get("/locations/modal"), "add-location")

    created_response = await async_client.post(
        "/locations",
        data={"name": "master-contract-location", "category": "test", "order": "10"},
    )
    _assert_mutation_success(created_response, "add-location")
    created = (
        db.query(models.Location)
        .filter(models.Location.name == "master-contract-location")
        .one()
    )

    duplicate_response = await async_client.post(
        "/locations",
        data={"name": "master-contract-location", "category": "test", "order": "20"},
    )
    _assert_inline_error(duplicate_response)

    _assert_open_modal(
        await async_client.get(f"/locations/modal/{created.id}"),
        f"edit-location-{created.id}",
    )
    updated_response = await async_client.put(
        f"/locations/{created.id}",
        data={
            "name": "master-contract-location-updated",
            "category": "updated",
            "order": "11",
        },
    )
    _assert_mutation_success(updated_response, f"edit-location-{created.id}")

    _assert_open_modal(
        await async_client.get(f"/locations/delete-modal/{created.id}"),
        f"location-delete-modal-{created.id}",
    )
    deleted_response = await async_client.delete(f"/locations/{created.id}")
    _assert_mutation_success(deleted_response, f"location-delete-modal-{created.id}")
    assert db.get(models.Location, created.id) is None


async def test_user_type_master_crud_uses_standard_modal_contract(
    async_client: AsyncClient,
    db: Session,
) -> None:
    _assert_open_modal(await async_client.get("/user-types/modal"), "add-user-type")

    created_response = await async_client.post(
        "/user-types",
        data={"name": "master-contract-user-type", "order": "10"},
    )
    _assert_mutation_success(created_response, "add-user-type")
    created = (
        db.query(models.UserType)
        .filter(models.UserType.name == "master-contract-user-type")
        .one()
    )

    duplicate_response = await async_client.post(
        "/user-types",
        data={"name": "master-contract-user-type", "order": "20"},
    )
    _assert_inline_error(duplicate_response)

    _assert_open_modal(
        await async_client.get(f"/user-types/modal/{created.id}"),
        f"edit-user-type-{created.id}",
    )
    updated_response = await async_client.put(
        f"/user-types/{created.id}",
        data={"name": "master-contract-user-type-updated", "order": "11"},
    )
    _assert_mutation_success(updated_response, f"edit-user-type-{created.id}")

    _assert_open_modal(
        await async_client.get(f"/user-types/delete-modal/{created.id}"),
        f"user-type-delete-modal-{created.id}",
    )
    deleted_response = await async_client.delete(f"/user-types/{created.id}")
    _assert_mutation_success(deleted_response, f"user-type-delete-modal-{created.id}")
    assert db.get(models.UserType, created.id) is None


async def test_holiday_master_crud_uses_standard_modal_contract(
    async_client: AsyncClient,
    db: Session,
) -> None:
    _assert_open_modal(
        await async_client.get("/holidays/modal"),
        "add-custom-holiday",
    )

    created_response = await async_client.post(
        "/holidays",
        data={"date": "2034-06-12", "name": "master-contract-holiday"},
    )
    _assert_mutation_success(created_response, "add-custom-holiday")
    created = (
        db.query(models.CustomHoliday)
        .filter(models.CustomHoliday.name == "master-contract-holiday")
        .one()
    )

    duplicate_response = await async_client.post(
        "/holidays",
        data={"date": "2034-06-12", "name": "duplicate-holiday"},
    )
    _assert_inline_error(duplicate_response)

    _assert_open_modal(
        await async_client.get(f"/holidays/modal/{created.id}"),
        f"edit-custom-holiday-{created.id}",
    )
    updated_response = await async_client.put(
        f"/holidays/{created.id}",
        data={"date": "2034-06-13", "name": "master-contract-holiday-updated"},
    )
    _assert_mutation_success(updated_response, f"edit-custom-holiday-{created.id}")

    _assert_open_modal(
        await async_client.get(f"/holidays/delete-modal/{created.id}"),
        f"custom-holiday-delete-modal-{created.id}",
    )
    deleted_response = await async_client.delete(f"/holidays/{created.id}")
    _assert_mutation_success(
        deleted_response,
        f"custom-holiday-delete-modal-{created.id}",
    )
    assert db.get(models.CustomHoliday, created.id) is None


async def test_user_master_crud_uses_standard_modal_contract(
    async_client: AsyncClient,
    db: Session,
) -> None:
    group = crud.group.create(
        db,
        obj_in=schemas.GroupCreate(name="master-contract-user-group", order=10),
    )
    user_type = crud.user_type.create(
        db,
        obj_in=schemas.UserTypeCreate(name="master-contract-user-type", order=10),
    )
    db.commit()
    assert group.id is not None and user_type.id is not None

    _assert_open_modal(await async_client.get("/users/modal"), "user-modal-new")

    created_response = await async_client.post(
        "/users",
        data={
            "id": "master-contract-user",
            "username": "Master Contract User",
            "group_id": str(group.id),
            "user_type_id": str(user_type.id),
        },
    )
    _assert_mutation_success(created_response, "user-modal-new")
    created = db.get(models.User, "master-contract-user")
    assert created is not None

    duplicate_response = await async_client.post(
        "/users",
        data={
            "id": "master-contract-user",
            "username": "Master Contract User Duplicate",
            "group_id": str(group.id),
            "user_type_id": str(user_type.id),
        },
    )
    _assert_inline_error(duplicate_response)

    _assert_open_modal(
        await async_client.get("/users/modal/master-contract-user"),
        "user-modal-master-contract-user",
    )
    updated_response = await async_client.put(
        "/users/master-contract-user",
        data={
            "username": "Master Contract User Updated",
            "group_id": str(group.id),
            "user_type_id": str(user_type.id),
        },
    )
    _assert_mutation_success(
        updated_response,
        "user-modal-master-contract-user",
    )

    _assert_open_modal(
        await async_client.get("/users/delete-modal/master-contract-user"),
        "user-delete-modal-master-contract-user",
    )
    deleted_response = await async_client.delete("/users/master-contract-user")
    _assert_mutation_success(
        deleted_response,
        "user-delete-modal-master-contract-user",
    )
    assert db.get(models.User, "master-contract-user") is None


@pytest.mark.parametrize("path", ["/users/rows", "/locations/rows", "/user-types/rows"])
async def test_legacy_row_mutation_endpoints_are_removed(
    async_client: AsyncClient,
    path: str,
) -> None:
    response = await async_client.post(path, data={})
    assert response.status_code == 405
