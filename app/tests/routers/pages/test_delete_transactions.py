from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app import crud, models
from app.schemas.group import GroupCreate
from app.schemas.location import LocationCreate
from app.schemas.user import UserCreate
from app.schemas.user_type import UserTypeCreate
from app.services import user_service


@pytest.mark.asyncio
async def test_group_page_delete_commits(
    async_client: AsyncClient, db: Session
) -> None:
    created = crud.group.create(db, obj_in=GroupCreate(name="page-delete-group"))
    db.commit()
    group_id = int(created.id)

    response = await async_client.delete(f"/groups/{group_id}")

    assert response.status_code == 200
    assert crud.group.get(db, id=group_id) is None


@pytest.mark.asyncio
async def test_location_page_delete_commits(
    async_client: AsyncClient, db: Session
) -> None:
    created = crud.location.create(
        db, obj_in=LocationCreate(name="page-delete-location")
    )
    db.commit()
    location_id = int(created.id)

    response = await async_client.delete(f"/locations/{location_id}")

    assert response.status_code == 200
    assert crud.location.get(db, id=location_id) is None


@pytest.mark.asyncio
async def test_user_type_page_delete_commits(
    async_client: AsyncClient, db: Session
) -> None:
    created = crud.user_type.create(
        db, obj_in=UserTypeCreate(name="page-delete-user-type")
    )
    db.commit()
    user_type_id = int(created.id)

    response = await async_client.delete(f"/user-types/{user_type_id}")

    assert response.status_code == 200
    assert crud.user_type.get(db, id=user_type_id) is None


@pytest.mark.asyncio
async def test_user_page_delete_commits_user_and_attendance(
    async_client: AsyncClient, db: Session
) -> None:
    group = crud.group.create(db, obj_in=GroupCreate(name="page-delete-user-group"))
    user_type = crud.user_type.create(
        db, obj_in=UserTypeCreate(name="page-delete-user-type")
    )
    location = crud.location.create(
        db, obj_in=LocationCreate(name="page-delete-user-location")
    )
    db.commit()

    created_user = user_service.create_user_with_validation(
        db,
        user_in=UserCreate(
            id="page-delete-user",
            username="Page Delete User",
            group_id=int(group.id),
            user_type_id=int(user_type.id),
        ),
    )
    db.add(
        models.Attendance(
            user_id=str(created_user.id),
            date=date(2030, 1, 1),
            location_id=int(location.id),
        )
    )
    db.commit()

    response = await async_client.delete(f"/users/{created_user.id}")

    assert response.status_code == 200
    assert crud.user.get(db, id=str(created_user.id)) is None
    assert (
        db.query(models.Attendance)
        .filter(models.Attendance.user_id == str(created_user.id))
        .count()
        == 0
    )
