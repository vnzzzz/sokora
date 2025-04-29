import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session

# モデルとスキーマ、CRUD操作をインポート
from app.models.user import User
from app.schemas.user import UserCreate
from app.crud.user import user as crud_user
from app.models.group import Group
from app.schemas.group import GroupCreate
from app.crud.group import group as crud_group
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate
from app.crud.user_type import user_type as crud_user_type

pytestmark = pytest.mark.asyncio


# --- Helper Function --- 
def create_test_dependencies(db: Session) -> tuple[Group, UserType]:
    """テストに必要な Group と UserType を作成するヘルパー関数"""
    test_group = crud_group.create(db, obj_in=GroupCreate(name="Test Group for User API"))
    test_user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name="Test UserType for User API"))
    db.commit()
    return test_group, test_user_type


# --- GET /api/users Tests ---

async def test_get_users_empty(async_client: AsyncClient) -> None:
    """
    ユーザーが登録されていない場合に空のリストが返されることをテストします。
    """
    response = await async_client.get("/api/users")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"users": []}


async def test_get_users_with_data(async_client: AsyncClient, test_app: FastAPI, db: Session) -> None:
    """
    ユーザーが登録されている場合にリストが正しく返されることをテストします。
    """
    # 依存関係を作成
    test_group, test_user_type = create_test_dependencies(db)
    
    # テストユーザーを作成
    user1 = crud_user.create(db, obj_in=UserCreate(user_id="user_b", username="User B", group_id=test_group.id, user_type_id=test_user_type.id)) # type: ignore
    user2 = crud_user.create(db, obj_in=UserCreate(user_id="user_a", username="User A", group_id=test_group.id, user_type_id=test_user_type.id)) # type: ignore
    db.commit()

    response = await async_client.get("/api/users")
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 2

    # APIは特定の順序を保証しないため、IDで存在を確認
    user_ids = {u['id'] for u in data['users']}
    assert user1.id in user_ids
    assert user2.id in user_ids
    # 必要であれば、より詳細な内容チェックを追加 


# --- GET /api/users/{user_id} Tests ---

async def test_get_user_success(async_client: AsyncClient, db: Session) -> None:
    """
    指定したIDのユーザーが正常に取得されることをテストします。
    """
    test_group, test_user_type = create_test_dependencies(db)
    user_id_to_get = "test_get_user"
    user_name = "Test Get User"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id_to_get, username=user_name, group_id=test_group.id, user_type_id=test_user_type.id)) # type: ignore
    db.commit()

    response = await async_client.get(f"/api/users/{user_id_to_get}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id_to_get
    assert data["username"] == user_name
    assert data["group_id"] == test_group.id
    assert data["user_type_id"] == test_user_type.id

async def test_get_user_not_found(async_client: AsyncClient) -> None:
    """
    存在しないユーザーIDを指定した場合に 404 エラーが返されることをテストします。
    """
    non_existent_user_id = "non_existent_user"
    response = await async_client.get(f"/api/users/{non_existent_user_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"] 


# --- POST /api/users Tests ---

async def test_create_user_success(async_client: AsyncClient, db: Session) -> None:
    """
    ユーザーが正常に作成されることをテストします。
    """
    test_group, test_user_type = create_test_dependencies(db)
    user_id = "new_user_success"
    username = "New User Success"
    payload = {
        "user_id": user_id,
        "username": username,
        "group_id": test_group.id,
        "user_type_id": test_user_type.id
    }
    response = await async_client.post("/api/users", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == username
    assert data["group_id"] == test_group.id
    assert data["user_type_id"] == test_user_type.id

    # DBでも確認
    db_user = db.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    assert db_user.username == username

async def test_create_user_missing_fields(async_client: AsyncClient, db: Session) -> None:
    """
    必須フィールドが欠落している場合に 422 エラーが返されることをテストします。
    """
    test_group, test_user_type = create_test_dependencies(db)
    base_payload = {
        "user_id": "missing_fields_user",
        "username": "Missing Fields User",
        "group_id": test_group.id,
        "user_type_id": test_user_type.id
    }

    for field in base_payload.keys():
        payload = base_payload.copy()
        del payload[field]
        response = await async_client.post("/api/users", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

async def test_create_user_duplicate_id(async_client: AsyncClient, db: Session) -> None:
    """
    重複するユーザーIDで作成しようとした場合に 400 エラーが返されることをテストします。
    """
    test_group, test_user_type = create_test_dependencies(db)
    user_id = "duplicate_user_id"
    # 最初のユーザーを作成
    crud_user.create(db, obj_in=UserCreate(user_id=user_id, username="First User", group_id=test_group.id, user_type_id=test_user_type.id)) # type: ignore
    db.commit()

    # 同じIDで再度作成
    payload = {
        "user_id": user_id,
        "username": "Second User",
        "group_id": test_group.id,
        "user_type_id": test_user_type.id
    }
    response = await async_client.post("/api/users", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "既に使用されています" in response.json()["detail"]

async def test_create_user_invalid_dependency_id(async_client: AsyncClient, db: Session) -> None:
    """
    存在しない group_id または user_type_id を指定した場合に 404 エラーが返されることをテストします。
    """
    test_group, test_user_type = create_test_dependencies(db)
    non_existent_id = 9999

    # ケース1: 無効な group_id
    payload_invalid_group = {
        "user_id": "invalid_group_user",
        "username": "Invalid Group User",
        "group_id": non_existent_id,
        "user_type_id": test_user_type.id
    }
    response_group = await async_client.post("/api/users", json=payload_invalid_group)
    assert response_group.status_code == status.HTTP_404_NOT_FOUND
    assert "Group with id" in response_group.json()["detail"] # crud の get_or_404 メッセージに依存

    # ケース2: 無効な user_type_id
    payload_invalid_user_type = {
        "user_id": "invalid_ut_user",
        "username": "Invalid UT User",
        "group_id": test_group.id,
        "user_type_id": non_existent_id
    }
    response_user_type = await async_client.post("/api/users", json=payload_invalid_user_type)
    assert response_user_type.status_code == status.HTTP_404_NOT_FOUND
    assert "UserType with id" in response_user_type.json()["detail"] # crud の get_or_404 メッセージに依存 


# --- PUT /api/users/{user_id} Tests ---

async def test_update_user_success(async_client: AsyncClient, db: Session) -> None:
    """
    ユーザー情報が正常に更新されることをテストします。
    """
    # 依存関係と初期ユーザーを作成
    group1, ut1 = create_test_dependencies(db)
    group2 = crud_group.create(db, obj_in=GroupCreate(name="Update Group"))
    ut2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Update UserType"))
    user_id_to_update = "user_to_update"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id_to_update, username="Original Name", group_id=group1.id, user_type_id=ut1.id)) # type: ignore
    db.commit()

    # 更新内容
    updated_username = "Updated Name"
    payload = {
        "username": updated_username,
        "group_id": group2.id,
        "user_type_id": ut2.id
    }

    response = await async_client.put(f"/api/users/{user_id_to_update}", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id_to_update
    assert data["username"] == updated_username
    assert data["group_id"] == group2.id
    assert data["user_type_id"] == ut2.id

    # DBでも確認
    db.refresh(user)
    assert user.username == updated_username
    assert user.group_id == group2.id
    assert user.user_type_id == ut2.id

async def test_update_user_not_found(async_client: AsyncClient, db: Session) -> None:
    """
    存在しないユーザーIDを指定して更新しようとした場合に 404 エラーが返されることをテストします。
    """
    test_group, test_user_type = create_test_dependencies(db)
    non_existent_user_id = "non_existent_user"
    payload = {
        "username": "Update Non Existent",
        "group_id": test_group.id,
        "user_type_id": test_user_type.id
    }
    response = await async_client.put(f"/api/users/{non_existent_user_id}", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

async def test_update_user_invalid_dependency_id(async_client: AsyncClient, db: Session) -> None:
    """
    更新時に存在しない group_id または user_type_id を指定した場合に 404 エラーが返されることをテストします。
    """
    # 依存関係と初期ユーザーを作成
    group1, ut1 = create_test_dependencies(db)
    user_id_to_update = "user_to_update_invalid_dep"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id_to_update, username="Original Name", group_id=group1.id, user_type_id=ut1.id)) # type: ignore
    db.commit()
    non_existent_id = 9999

    # ケース1: 無効な group_id
    payload_invalid_group = {
        "username": "Updated Invalid Group",
        "group_id": non_existent_id,
        "user_type_id": ut1.id
    }
    response_group = await async_client.put(f"/api/users/{user_id_to_update}", json=payload_invalid_group)
    assert response_group.status_code == status.HTTP_404_NOT_FOUND
    assert "Group with id" in response_group.json()["detail"]

    # ケース2: 無効な user_type_id
    payload_invalid_user_type = {
        "username": "Updated Invalid UT",
        "group_id": group1.id,
        "user_type_id": non_existent_id
    }
    response_user_type = await async_client.put(f"/api/users/{user_id_to_update}", json=payload_invalid_user_type)
    assert response_user_type.status_code == status.HTTP_404_NOT_FOUND
    assert "UserType with id" in response_user_type.json()["detail"] 


# --- DELETE /api/users/{user_id} Tests ---

async def test_delete_user_success(async_client: AsyncClient, db: Session) -> None:
    """
    ユーザーが正常に削除されることをテストします。
    """
    # 依存関係とユーザーを作成
    test_group, test_user_type = create_test_dependencies(db)
    user_id_to_delete = "user_to_delete"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id_to_delete, username="User To Delete", group_id=test_group.id, user_type_id=test_user_type.id)) # type: ignore
    db.commit()

    # ユーザー削除
    response = await async_client.delete(f"/api/users/{user_id_to_delete}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # DBから削除されたか確認
    deleted_user = db.query(User).filter(User.id == user_id_to_delete).first()
    assert deleted_user is None

async def test_delete_user_not_found(async_client: AsyncClient) -> None:
    """
    存在しないユーザーIDを指定して削除しようとした場合に 404 エラーが返されることをテストします。
    """
    non_existent_user_id = "non_existent_user"
    response = await async_client.delete(f"/api/users/{non_existent_user_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]

# ユーザー削除時に勤怠データも削除されるため、in_use のテストは不要
# async def test_delete_user_in_use(async_client: AsyncClient, db: Session) -> None:
#     ... 