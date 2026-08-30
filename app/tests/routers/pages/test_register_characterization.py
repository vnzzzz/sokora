from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.crud import group as crud_group
from app.crud import location as crud_location
from app.crud import user as crud_user
from app.crud import user_type as crud_user_type
from app.schemas.group import GroupCreate
from app.schemas.location import LocationCreate
from app.schemas.user import UserCreate
from app.schemas.user_type import UserTypeCreate


async def test_monthly_registration_htmx_returns_user_list_fragment(
    async_client: AsyncClient,
    db: Session,
) -> None:
    group = crud_group.create(db, obj_in=GroupCreate(name="Characterization Group"))
    user_type = crud_user_type.create(
        db, obj_in=UserTypeCreate(name="Characterization Type")
    )
    crud_location.create(db, obj_in=LocationCreate(name="Characterization Location"))
    crud_user.create(
        db,
        obj_in=UserCreate(
            id="CHAR-001",
            username="Characterization User",
            group_id=int(group.id),
            user_type_id=int(user_type.id),
        ),
    )
    db.commit()

    response = await async_client.get(
        "/attendance/monthly?month=2024-12",
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["HX-Reswap"] == "outerHTML"
    assert '<div id="user-list"' in response.text
    assert "Characterization User" in response.text
    assert 'hx-get="/attendance/monthly/users/CHAR-001?month=2024-12"' in response.text
    assert "<!DOCTYPE html>" not in response.text
