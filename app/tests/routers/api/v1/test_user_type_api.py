import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session

from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate # Create スキーマをインポート

pytestmark = pytest.mark.asyncio

# API エンドポイントのベースパス
API_ENDPOINT = "/api/user_types"

async def test_get_user_types_empty(async_client: AsyncClient) -> None:
    """
    社員種別が登録されていない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get(API_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"user_types": []}

async def test_get_user_types_with_data(async_client: AsyncClient, test_app: FastAPI, db: Session) -> None:
    """
    社員種別が登録されている場合にリストが正しく返されることをテストします。
    """
    from app.crud.user_type import user_type as crud_user_type

    user_type1 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Test Type B"))
    user_type2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Test Type A"))
    db.commit()

    response = await async_client.get(API_ENDPOINT)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "user_types" in data
    assert len(data["user_types"]) == 2

    # APIは名前順で返すはず
    assert data["user_types"][0]["name"] == "Test Type A"
    assert data["user_types"][0]["id"] == user_type2.id
    assert data["user_types"][1]["name"] == "Test Type B"
    assert data["user_types"][1]["id"] == user_type1.id

async def test_create_user_type_success(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/user_types - 社員種別が正常に作成されることをテストします。
    """
    user_type_name = "New Test UserType"
    payload = {"name": user_type_name}

    response = await async_client.post(API_ENDPOINT, json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == user_type_name
    assert "id" in data
    user_type_id = data["id"]

    # DBに実際に作成されたかを確認
    db_user_type = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert db_user_type is not None
    assert db_user_type.name == user_type_name

async def test_create_user_type_missing_name(async_client: AsyncClient) -> None:
    """
    POST /api/user_types - 社員種別名がない場合に 400/422 エラーが返されることをテストします。
    """
    # ケース1: name が空文字列 (サービス層で 400)
    payload_empty = {"name": ""}
    response_empty = await async_client.post(API_ENDPOINT, json=payload_empty)
    assert response_empty.status_code == status.HTTP_400_BAD_REQUEST
    assert response_empty.json()["detail"] == "社員種別名を入力してください"

    # ケース2: name フィールド自体がない (不正なスキーマ、Pydantic が 422)
    payload_no_name: dict = {}
    response_no_name = await async_client.post(API_ENDPOINT, json=payload_no_name)
    assert response_no_name.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_create_user_type_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    POST /api/user_types - 重複する社員種別名で作成しようとした場合に 400 エラーが返されることをテストします。
    """
    from app.crud.user_type import user_type as crud_user_type

    user_type_name = "Duplicate UserType"
    # 最初に社員種別を作成しておく
    crud_user_type.create(db, obj_in=UserTypeCreate(name=user_type_name))
    db.commit()

    # 同じ名前で再度作成しようとする
    payload = {"name": user_type_name}
    response = await async_client.post(API_ENDPOINT, json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "この社員種別名は既に存在します"

async def test_update_user_type_success(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/user_types/{user_type_id} - 社員種別が正常に更新されることをテストします。
    """
    from app.crud.user_type import user_type as crud_user_type

    # 更新対象の社員種別を作成
    original_name = "Original UserType Name"
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name=original_name))
    db.commit()
    user_type_id = user_type_to_update.id

    # 更新後の名前
    updated_name = "Updated UserType Name"
    payload = {"name": updated_name}

    response = await async_client.put(f"{API_ENDPOINT}/{user_type_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == updated_name
    assert data["id"] == user_type_id

    # DBで実際に更新されたかを確認
    db.refresh(user_type_to_update)
    assert user_type_to_update.name == updated_name

async def test_update_user_type_not_found(async_client: AsyncClient) -> None:
    """
    PUT /api/user_types/{user_type_id} - 存在しない社員種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_user_type_id = 9999
    payload = {"name": "Non Existent Update"}

    response = await async_client.put(f"{API_ENDPOINT}/{non_existent_user_type_id}", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_update_user_type_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/user_types/{user_type_id} - 他の社員種別が使用中の名前に更新しようとした場合に 400 エラーが返されることをテストします。
    """
    from app.crud.user_type import user_type as crud_user_type

    # 2つの社員種別を作成
    user_type1 = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType To Update"))
    user_type2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Existing Other UserType"))
    db.commit()
    user_type_id_to_update = user_type1.id
    existing_name = user_type2.name

    # user_type1 の名前を user_type2 と同じにしようとする
    payload = {"name": existing_name}
    response = await async_client.put(f"{API_ENDPOINT}/{user_type_id_to_update}", json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]

async def test_update_user_type_same_name(async_client: AsyncClient, db: Session) -> None:
    """
    PUT /api/user_types/{user_type_id} - 同じ名前で更新しても正常に完了することをテストします。
    """
    from app.crud.user_type import user_type as crud_user_type

    # 更新対象の社員種別を作成
    original_name = "Same Name UserType"
    user_type_to_update = crud_user_type.create(db, obj_in=UserTypeCreate(name=original_name))
    db.commit()
    user_type_id = user_type_to_update.id

    # 同じ名前で更新
    payload = {"name": original_name}
    response = await async_client.put(f"{API_ENDPOINT}/{user_type_id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == original_name
    assert data["id"] == user_type_id

    # DB で名前が変わっていないことを確認
    db.refresh(user_type_to_update)
    assert user_type_to_update.name == original_name

async def test_delete_user_type_success(async_client: AsyncClient, db: Session) -> None:
    """
    DELETE /api/user_types/{user_type_id} - 社員種別が正常に削除されることをテストします。
    """
    from app.crud.user_type import user_type as crud_user_type

    # 削除対象の社員種別を作成
    user_type_to_delete = crud_user_type.create(db, obj_in=UserTypeCreate(name="UserType To Delete"))
    db.commit()
    user_type_id = user_type_to_delete.id

    # 社員種別を削除
    response = await async_client.delete(f"{API_ENDPOINT}/{user_type_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # DBから削除されたかを確認
    deleted_user_type = db.query(UserType).filter(UserType.id == user_type_id).first()
    assert deleted_user_type is None

async def test_delete_user_type_not_found(async_client: AsyncClient) -> None:
    """
    DELETE /api/user_types/{user_type_id} - 存在しない社員種別IDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_user_type_id = 9999

    response = await async_client.delete(f"{API_ENDPOINT}/{non_existent_user_type_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"] 