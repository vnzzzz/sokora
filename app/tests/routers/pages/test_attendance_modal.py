import datetime

from app.crud import group as crud_group
from app.crud import user_type as crud_user_type
from app.crud import location as crud_location
from app.crud import user as crud_user
from app.schemas.group import GroupCreate
from app.schemas.user_type import UserTypeCreate
from app.schemas.location import LocationCreate
from app.schemas.user import UserCreate


async def test_attendance_modal_can_be_loaded(async_client, db) -> None:
    """勤怠モーダルが 404 にならず取得できる"""
    group = crud_group.create(db, obj_in=GroupCreate(name="テストグループ"))
    user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name="テスト種別"))
    crud_location.create(db, obj_in=LocationCreate(name="出社"))
    crud_user.create(
        db,
        obj_in=UserCreate(
            id="U001",
            username="テスト太郎",
            group_id=group.id,
            user_type_id=user_type.id,
        ),
    )
    db.commit()

    target_date = datetime.date(2024, 12, 1)
    response = await async_client.get(f"/attendance/modals/U001/{target_date}?mode=register")

    assert response.status_code == 200
    assert "勤怠編集" in response.text
    assert "U001" in response.text
