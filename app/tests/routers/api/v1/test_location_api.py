import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session

from app.models.location import Location
from app.schemas.location import LocationCreate # Create スキーマをインポート

pytestmark = pytest.mark.asyncio

# API エンドポイントのベースパス
API_ENDPOINT = "/api/v1/locations"

async def test_get_locations_empty(async_client: AsyncClient) -> None:
    """
    勤怠種別が登録されていない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get(API_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"locations": []}

async def test_get_locations_with_data(async_client: AsyncClient, test_app: FastAPI, db: Session) -> None:
    """
    勤怠種別が登録されている場合にリストが正しく返されることをテストします。
    """
    from app.crud.location import location as crud_location

    location1 = crud_location.create(db, obj_in=LocationCreate(name="Test Location B"))
    location2 = crud_location.create(db, obj_in=LocationCreate(name="Test Location A"))
    db.commit()

    response = await async_client.get(API_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "locations" in data
    assert len(data["locations"]) == 2

    # APIは名前順で返すはず
    assert data["locations"][0]["name"] == "Test Location A"
    assert data["locations"][0]["id"] == location2.id
    assert data["locations"][1]["name"] == "Test Location B"
    assert data["locations"][1]["id"] == location1.id

async def test_create_location_success(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/v1/locations - 勤怠種別が正常に作成されることをテストします。
    """
    location_name = "New Test Location"
    payload = {"name": location_name}

    response = await async_client.post(API_ENDPOINT, json=payload)

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
    POST /api/v1/locations - 勤怠種別名がない場合に 400/422 エラーが返されることをテストします。
    """
    # ケース1: name が空文字列 (サービス層で 400)
    payload_empty = {"name": ""}
    response_empty = await async_client.post(API_ENDPOINT, json=payload_empty)
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST
    assert response_empty.json()["detail"] == "勤怠種別名を入力してください"

    # ケース2: name フィールド自体がない (不正なスキーマ、Pydantic が 422)
    payload_no_name: dict = {}
    response_no_name = await async_client.post(API_ENDPOINT, json=payload_no_name)
    assert response_no_name.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_create_location_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/v1/locations - 重複する勤怠種別名で作成しようとした場合に 400 エラーが返されることをテストします。
    """
    from app.crud.location import location as crud_location

    location_name = "Duplicate Location"
    # 最初に勤怠種別を作成しておく
    crud_location.create(db, obj_in=LocationCreate(name=location_name))
    db.commit()

    # 同じ名前で再度作成しようとする
    payload = {"name": location_name}
    response = await async_client.post(API_ENDPOINT, json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "この勤怠種別名は既に存在します" # サービス層のエラーメッセージに合わせる

async def test_update_location_success(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/v1/locations/{location_id} - 勤怠種別が正常に更新されることをテストします。
    """
    from app.crud.location import location as crud_location

    # 更新対象の勤怠種別を作成
    original_name = "Original Location Name"
    location_to_update = crud_location.create(db, obj_in=LocationCreate(name=original_name))
    db.commit()
    location_id = location_to_update.id

    # 更新後の名前
    updated_name = "Updated Location Name"
    payload = {"name": updated_name}

    response = await async_client.put(f"{API_ENDPOINT}/{location_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == updated_name
    assert data["id"] == location_id

    # DBで実際に更新されたかを確認
    db.refresh(location_to_update)
    assert location_to_update.name == updated_name

async def test_update_location_not_found(async_client: AsyncClient) -> None:
    """
    PUT /api/v1/locations/{location_id} - 存在しない勤怠種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_location_id = 9999
    payload = {"name": "Non Existent Update"}

    response = await async_client.put(f"{API_ENDPOINT}/{non_existent_location_id}", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_update_location_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/v1/locations/{location_id} - 他の勤怠種別が使用中の名前に更新しようとした場合に 400 エラーが返されることをテストします。
    """
    from app.crud.location import location as crud_location

    # 2つの勤怠種別を作成
    location1 = crud_location.create(db, obj_in=LocationCreate(name="Location To Update"))
    location2 = crud_location.create(db, obj_in=LocationCreate(name="Existing Other Location"))
    db.commit()
    location_id_to_update = location1.id
    existing_name = location2.name

    # location1 の名前を location2 と同じにしようとする
    payload = {"name": existing_name}
    response = await async_client.put(f"{API_ENDPOINT}/{location_id_to_update}", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]

async def test_update_location_same_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/v1/locations/{location_id} - 同じ名前で更新しても正常に完了することをテストします。
    """
    from app.crud.location import location as crud_location

    # 更新対象の勤怠種別を作成
    original_name = "Same Name Location"
    location_to_update = crud_location.create(db, obj_in=LocationCreate(name=original_name))
    db.commit()
    location_id = location_to_update.id

    # 同じ名前で更新
    payload = {"name": original_name}
    response = await async_client.put(f"{API_ENDPOINT}/{location_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == original_name
    assert data["id"] == location_id

    # DB で名前が変わっていないことを確認
    db.refresh(location_to_update)
    assert location_to_update.name == original_name

async def test_delete_location_success(async_client: AsyncClient, db: Session) -> None:
    """
    DELETE /api/v1/locations/{location_id} - 勤怠種別が正常に削除されることをテストします。
    """
    from app.crud.location import location as crud_location

    # 削除対象の勤怠種別を作成
    location_to_delete = crud_location.create(db, obj_in=LocationCreate(name="Location To Delete"))
    db.commit()
    location_id = location_to_delete.id

    # 勤怠種別を削除
    response = await async_client.delete(f"{API_ENDPOINT}/{location_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # DBから削除されたかを確認
    deleted_location = db.query(Location).filter(Location.id == location_id).first()
    assert deleted_location is None

async def test_delete_location_not_found(async_client: AsyncClient) -> None:
    """
    DELETE /api/v1/locations/{location_id} - 存在しない勤怠種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_location_id = 9999

    response = await async_client.delete(f"{API_ENDPOINT}/{non_existent_location_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"] 