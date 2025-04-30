import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session

# モデルとスキーマ、CRUD操作をインポート
from app.models.location import Location
from app.schemas.location import LocationCreate
from app.crud.location import location as crud_location
# Attendance 関連のインポートを追加
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate # 必要に応じて
from app.crud.attendance import attendance as crud_attendance
from app.models.user import User # Attendance は User に依存
from app.schemas.user import UserCreate # User 作成用
from app.crud.user import user as crud_user
# User は Group, UserType に依存
from app.models.group import Group
from app.schemas.group import GroupCreate
from app.crud.group import group as crud_group
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate
from app.crud.user_type import user_type as crud_user_type
from datetime import date

pytestmark = pytest.mark.asyncio


async def test_get_locations_empty(async_client: AsyncClient) -> None:
    """
    勤務場所が登録されていない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get("/api/locations")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"locations": []}


async def test_get_locations_with_data(async_client: AsyncClient, test_app: FastAPI, db: Session) -> None:
    """
    勤務場所が登録されている場合にリストが正しく返されることをテストします。
    """
    # テストデータの作成
    loc1 = crud_location.create(db, obj_in=LocationCreate(name="Location B"))
    loc2 = crud_location.create(db, obj_in=LocationCreate(name="Location A"))
    db.commit()

    response = await async_client.get("/api/locations")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "locations" in data
    assert len(data["locations"]) == 2

    # APIは名前順で返すはず
    assert data["locations"][0]["name"] == "Location A"
    assert data["locations"][0]["id"] == loc2.id
    assert data["locations"][1]["name"] == "Location B"
    assert data["locations"][1]["id"] == loc1.id


# --- POST /api/locations Tests ---

async def test_create_location_success(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/locations - 勤務場所が正常に作成されることをテストします。
    """
    location_name = "New Test Location"
    payload = {"name": location_name}
    
    response = await async_client.post("/api/locations", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == location_name
    assert "id" in data
    location_id = data["id"]

    # DBに実際に作成されたかを確認
    db_location = db.query(Location).filter(Location.id == location_id).first()
    assert db_location is not None
    assert db_location.name == location_name

async def test_create_location_missing_name(async_client: AsyncClient) -> None:
    """
    POST /api/locations - 勤務場所名がない場合にエラーが返されることをテストします。
    """
    # ケース1: name が空文字列 (400 Bad Request)
    payload_empty = {"name": ""}
    response_empty = await async_client.post("/api/locations", json=payload_empty)
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST
    assert response_empty.json()["detail"] == "勤務場所名を入力してください"

    # ケース2: name フィールド自体がない (422 Unprocessable Entity)
    payload_no_name: dict = {}
    response_no_name = await async_client.post("/api/locations", json=payload_no_name)
    assert response_no_name.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_create_location_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/locations - 重複する勤務場所名で作成しようとした場合に 400 エラーが返されることをテストします。
    """
    location_name = "Duplicate Location"
    # 最初に勤務場所を作成しておく（API経由で）
    await async_client.post("/api/locations", json={"name": location_name})
    # db.commit() # APIコール内でコミットされるはず

    # 同じ名前で再度作成しようとする
    payload = {"name": location_name}
    response = await async_client.post("/api/locations", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # サービス層が返すエラーメッセージに合わせる
    assert response.json()["detail"] == "この勤務場所名は既に存在します"


# --- PUT /api/locations/{location_id} Tests ---

async def test_update_location_success(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/locations/{location_id} - 勤務場所が正常に更新されることをテストします。
    """
    original_name = "Original Location Name"
    location_to_update = crud_location.create(db, obj_in=LocationCreate(name=original_name))
    db.commit()
    location_id = location_to_update.id
    
    updated_name = "Updated Location Name"
    payload = {"name": updated_name}
    
    response = await async_client.put(f"/api/locations/{location_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == updated_name
    assert data["id"] == location_id

    db.refresh(location_to_update)
    assert location_to_update.name == updated_name

async def test_update_location_not_found(async_client: AsyncClient) -> None:
    """
    PUT /api/locations/{location_id} - 存在しない勤務場所IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_location_id = 9999
    payload = {"name": "Non Existent Update"}
    response = await async_client.put(f"/api/locations/{non_existent_location_id}", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_update_location_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/locations/{location_id} - 他の勤務場所が使用中の名前に更新しようとした場合に 400 エラーが返されることをテストします。
    """
    loc1 = crud_location.create(db, obj_in=LocationCreate(name="Location To Update"))
    loc2 = crud_location.create(db, obj_in=LocationCreate(name="Existing Other Location"))
    db.commit()
    location_id_to_update = loc1.id
    existing_name = loc2.name

    payload = {"name": existing_name}
    response = await async_client.put(f"/api/locations/{location_id_to_update}", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]

async def test_update_location_same_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/locations/{location_id} - 同じ名前で更新しても正常に完了することをテストします。
    """
    original_name = "Same Name Location"
    location_to_update = crud_location.create(db, obj_in=LocationCreate(name=original_name))
    db.commit()
    location_id = location_to_update.id
    
    payload = {"name": original_name}
    response = await async_client.put(f"/api/locations/{location_id}", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == original_name
    assert data["id"] == location_id

    db.refresh(location_to_update)
    assert location_to_update.name == original_name


# --- DELETE /api/locations/{location_id} Tests ---

async def test_delete_location_success(async_client: AsyncClient, db: Session) -> None:
    """
    DELETE /api/locations/{location_id} - 勤務場所が正常に削除されることをテストします。
    """
    location_to_delete = crud_location.create(db, obj_in=LocationCreate(name="Location To Delete"))
    db.commit()
    location_id = location_to_delete.id

    response = await async_client.delete(f"/api/locations/{location_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    deleted_location = db.query(Location).filter(Location.id == location_id).first()
    assert deleted_location is None

async def test_delete_location_not_found(async_client: AsyncClient) -> None:
    """
    DELETE /api/locations/{location_id} - 存在しない勤務場所IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_location_id = 9999
    response = await async_client.delete(f"/api/locations/{non_existent_location_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_delete_location_in_use(async_client: AsyncClient, db: Session) -> None:
    """
    DELETE /api/locations/{location_id} - 勤怠データで使用中の勤務場所を削除しようとした場合にエラーが発生することをテストします。
    """
    # 依存関係の準備: Group, UserType, User
    group = crud_group.create(db, obj_in=GroupCreate(name="Test Group for Loc Delete"))
    user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name="Test UserType for Loc Delete"))
    db.commit()
    user_id_for_test = "testuser_locdel"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id_for_test, username="Test User LocDel", group_id=group.id, user_type_id=user_type.id)) # type: ignore
    db.commit()

    # 削除対象の勤務場所を作成
    location_to_delete = crud_location.create(db, obj_in=LocationCreate(name="Location In Use"))
    db.commit()
    location_id = location_to_delete.id

    # この勤務場所を使用する勤怠データを作成
    attendance_date = date.today()
    # AttendanceCreate を使う代わりに、Attendance モデルオブジェクトを直接作成
    attendance_record = Attendance(
        user_id=user_id_for_test,
        date=attendance_date,
        location_id=location_id
    )
    db.add(attendance_record)
    # crud_attendance.create(
    #     db, obj_in=AttendanceCreate(user_id=user_id_for_test, date=attendance_date, location_id=location_id) # type: ignore
    # )
    db.commit()

    # 勤務場所を削除しようとする
    response = await async_client.delete(f"/api/locations/{location_id}")

    # crud.location.remove 内でチェックされるはず (400 Bad Request)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "使用されているため削除できません" in response.json()["detail"]

    # DBに残っていることを確認
    location_still_exists = db.query(Location).filter(Location.id == location_id).first()
    assert location_still_exists is not None 