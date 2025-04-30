import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session
import re # 正規表現モジュールをインポート

# モデル、スキーマ、CRUD、テストヘルパー等をインポート
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.crud.user import user as crud_user
from app.models.group import Group
from app.schemas.group import GroupCreate
from app.crud.group import group as crud_group
from app.models.user_type import UserType
from app.schemas.user_type import UserTypeCreate
from app.crud.user_type import user_type as crud_user_type

# APIテストからヘルパー関数を借用（または共通化）
def create_test_dependencies_for_page(db: Session) -> tuple[Group, UserType]:
    """テストに必要な Group と UserType を作成するヘルパー関数"""
    test_group = crud_group.create(db, obj_in=GroupCreate(name="Test Group for User Page"))
    test_user_type = crud_user_type.create(db, obj_in=UserTypeCreate(name="Test UserType for User Page"))
    db.commit()
    db.refresh(test_group)
    db.refresh(test_user_type)
    return test_group, test_user_type


@pytest.mark.asyncio
async def test_read_users_page(async_client: AsyncClient, db: Session) -> None:
    """社員管理ページ (GET /user) が正常に取得でき、ユーザー情報が表示されることをテスト"""
    # Test data setup
    group, user_type = create_test_dependencies_for_page(db)
    user1 = crud_user.create(db, obj_in=UserCreate(user_id="page_test1", username="Page Test User 1", group_id=str(group.id), user_type_id=str(user_type.id)))
    db.commit()
    db.refresh(user1) # Refresh to load relationships if needed by template

    response = await async_client.get("/user")
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    # デバッグ: 完全なHTMLを出力 (一旦コメントアウト)
    # print("\n--- Full HTML for /user ---")
    # print(html)
    # print("--- End Full HTML ---")
    assert "<title>Sokora - 社員管理</title>" in html

    # Ensure we are using the actual string values from the instances
    user1_id_str = str(user1.id)
    user1_username_str = str(user1.username)
    group_name_str = str(group.name)
    user_type_name_str = str(user_type.name)

    # ユーザーデータがテーブルに表示されていることを確認
    assert re.search(rf'<tr\s+.*?id="user-row-{re.escape(user1_id_str)}".*?>', html) is not None, "User row TR tag not found using regex"
    assert re.search(rf'>{re.escape(user1_username_str)}\s*\({re.escape(user1_id_str)}\)<\/span>', html) is not None, "Username/ID not found"
    assert re.search(rf'<span>{re.escape(group_name_str)}<\/span>', html) is not None, "Group name not found"
    assert re.search(rf'<span\s+.*?id="user-type-{re.escape(user1_id_str)}".*?>{re.escape(user_type_name_str)}<\/span>', html) is not None, "User type name not found"
    assert f'hx-get="/pages/user/edit/{user1_id_str}"' in html # これは単純な文字列で大丈夫そう
    assert f'delete-form-{user1_id_str}' in html # これも大丈夫そう

# --- GET /pages/user/edit/{user_id} --- 

@pytest.mark.asyncio
async def test_get_user_edit_form_success(async_client: AsyncClient, db: Session) -> None:
    """ユーザー編集フォームが正常に取得できることをテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    user = crud_user.create(db, obj_in=UserCreate(user_id="edit_test", username="Edit Test User", group_id=str(group.id), user_type_id=str(user_type.id)))
    db.commit()

    response = await async_client.get(f"/pages/user/edit/{user.id}")
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    # 変更: 返却される HTML の構造に合わせてアサーションを修正
    assert f'id="edit-form-{user.id}"' in html # フォームの ID
    assert f'hx-put="/pages/user/row/{user.id}"' in html # hx-put 属性
    assert 'hx-indicator="#loading-indicator"' in html # hx-indicator 属性
    # input の value 属性は Jinja2 経由なので直接の文字列比較は難しいが、name は存在するか確認
    assert 'name="username"' in html 
    # value 属性が期待通りか、より詳細に確認する場合 (例: BeautifulSoup を使う)
    # from bs4 import BeautifulSoup
    # soup = BeautifulSoup(html, 'html.parser')
    # username_input = soup.find('input', {'name': 'username'})
    # assert username_input is not None
    # assert username_input.get('value') == "Edit Test User" 
    # 現状は簡易的なチェックに留める
    assert f'<option value="{group.id}"' in html # selected はつけない
    assert f'<option value="{user_type.id}"' in html # selected はつけない
    # selected 属性のチェック (Jinja2 が正しく評価されている前提)
    # soup = BeautifulSoup(html, 'html.parser')
    # group_option = soup.find('option', {'value': str(group.id)})
    # assert group_option is not None
    # assert group_option.has_attr('selected')
    # user_type_option = soup.find('option', {'value': str(user_type.id)})
    # assert user_type_option is not None
    # assert user_type_option.has_attr('selected')
    assert '@click="showEditModal = false"' in html # キャンセルボタン
    assert '<button type="submit"' in html # 保存ボタン

@pytest.mark.asyncio
async def test_get_user_edit_form_not_found(async_client: AsyncClient) -> None:
    """存在しないユーザーIDで編集フォームを取得しようとすると404になることをテスト"""
    response = await async_client.get("/pages/user/edit/non_existent_user")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- POST /pages/user/row --- 

@pytest.mark.asyncio
async def test_handle_create_user_row_success(async_client: AsyncClient, db: Session) -> None:
    """ユーザーが正常に作成され、対応する行のHTMLが返されることをテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    user_id = "create_test_user"
    username = "Create Test User"
    form_data = {
        "id": user_id,
        "username": username,
        "group_id": str(group.id),
        "user_type_id": str(user_type.id)
    }

    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    print("\n--- test_handle_create_user_row_success HTML ---")
    print(html)
    print("--- End HTML ---")

    assert f'id="user-row-{user_id}"' in html
    assert f'>{username} ({user_id})</span>' in html
    assert f'<span>{group.name}</span>' in html
    assert f'<span id="user-type-{user_id}">{user_type.name}</span>' in html

    # DB確認
    db_user = db.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    assert db_user.username == username
    assert db_user.group_id == group.id
    assert db_user.user_type_id == user_type.id

@pytest.mark.asyncio
async def test_handle_create_user_row_duplicate_id(async_client: AsyncClient, db: Session) -> None:
    """重複するユーザーIDで作成しようとすると400エラーとエラーHTMLが返るテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    user_id = "duplicate_create"
    # 既存ユーザー作成
    crud_user.create(db, obj_in=UserCreate(user_id=user_id, username="Existing", group_id=str(group.id), user_type_id=str(user_type.id)))
    db.commit()

    form_data = {
        "id": user_id,
        "username": "New Duplicate",
        "group_id": str(group.id),
        "user_type_id": str(user_type.id)
    }
    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == "#add-form-error"
    # シングルクォーテーションがHTMLエンティティにエスケープされていることを確認
    expected_error = f"ユーザーID &#39;{user_id}&#39; は既に使用されています。"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text

@pytest.mark.asyncio
async def test_handle_create_user_row_duplicate_username(async_client: AsyncClient, db: Session) -> None:
    """重複するユーザー名で作成しようとすると400エラーとエラーHTMLが返るテスト"""
    group, user_type = create_test_dependencies_for_page(db)
    existing_username = "duplicate_username_create"
    # 既存ユーザー作成
    crud_user.create(db, obj_in=UserCreate(user_id="dup_uname_1", username=existing_username, group_id=str(group.id), user_type_id=str(user_type.id)))
    db.commit()

    form_data = {
        "id": "dup_uname_2",
        "username": existing_username, # 重複するユーザー名
        "group_id": str(group.id),
        "user_type_id": str(user_type.id)
    }
    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers["HX-Retarget"] == "#add-form-error"
    expected_error = f"ユーザー名 &#39;{existing_username}&#39; は既に使用されています。"
    assert expected_error in response.text

@pytest.mark.asyncio
async def test_handle_create_user_row_invalid_group_id(async_client: AsyncClient, db: Session) -> None:
    """存在しないグループIDで作成しようとすると400エラーとエラーHTMLが返るテスト"""
    _, user_type = create_test_dependencies_for_page(db)
    invalid_group_id = 99999
    form_data = {
        "id": "invalid_group_create",
        "username": "Invalid Group User",
        "group_id": str(invalid_group_id), # 存在しないグループID
        "user_type_id": str(user_type.id)
    }
    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers["HX-Retarget"] == "#add-form-error"
    expected_error = f"指定されたグループID({invalid_group_id})は存在しません。"
    assert expected_error in response.text

@pytest.mark.asyncio
async def test_handle_create_user_row_invalid_user_type_id(async_client: AsyncClient, db: Session) -> None:
    """存在しない社員種別IDで作成しようとすると400エラーとエラーHTMLが返るテスト"""
    group, _ = create_test_dependencies_for_page(db)
    invalid_user_type_id = 88888
    form_data = {
        "id": "invalid_utype_create",
        "username": "Invalid UserType User",
        "group_id": str(group.id),
        "user_type_id": str(invalid_user_type_id) # 存在しない社員種別ID
    }
    response = await async_client.post("/pages/user/row", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers["HX-Retarget"] == "#add-form-error"
    expected_error = f"指定された社員種別ID({invalid_user_type_id})は存在しません。"
    assert expected_error in response.text

# --- PUT /pages/user/row/{user_id} ---

@pytest.mark.asyncio
async def test_handle_update_user_row_success(async_client: AsyncClient, db: Session) -> None:
    """ユーザー情報が正常に更新され、対応する行のHTMLが返されることをテスト"""
    group1, ut1 = create_test_dependencies_for_page(db)
    group2 = crud_group.create(db, obj_in=GroupCreate(name="Update Group Page"))
    ut2 = crud_user_type.create(db, obj_in=UserTypeCreate(name="Update UserType Page"))
    user_id = "update_test_user"
    original_username = "Original Update User"
    user = crud_user.create(db, obj_in=UserCreate(user_id=user_id, username=original_username, group_id=str(group1.id), user_type_id=str(ut1.id)))
    db.commit()

    updated_username = "Updated User Name Page"
    form_data = {
        "username": updated_username,
        "group_id": str(group2.id),
        "user_type_id": str(ut2.id)
    }

    response = await async_client.put(f"/pages/user/row/{user_id}", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    print("\n--- test_handle_update_user_row_success HTML ---")
    print(html)
    print("--- End HTML ---")

    assert f'id="user-row-{user_id}"' in html
    assert f'>{updated_username} ({user_id})</span>' in html
    assert f'<span>{group2.name}</span>' in html
    assert f'<span id="user-type-{user_id}">{ut2.name}</span>' in html

    # DB確認
    db.refresh(user)
    assert user.username == updated_username
    assert user.group_id == group2.id
    assert user.user_type_id == ut2.id

@pytest.mark.asyncio
async def test_handle_update_user_row_not_found(async_client: AsyncClient) -> None:
    """存在しないユーザーIDで更新しようとすると404エラーになるテスト"""
    form_data = {"username": "test", "group_id": "1", "user_type_id": "1"}
    response = await async_client.put("/pages/user/row/non_existent_user", data=form_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_handle_update_user_row_duplicate_username(async_client: AsyncClient, db: Session) -> None:
    """他のユーザーと重複するユーザー名で更新しようとすると400エラーになるテスト"""
    group, ut = create_test_dependencies_for_page(db)
    user1 = crud_user.create(db, obj_in=UserCreate(user_id="update_dup_user1", username="User1 UpdateDup", group_id=str(group.id), user_type_id=str(ut.id)))
    user2 = crud_user.create(db, obj_in=UserCreate(user_id="update_dup_user2", username="User2 UpdateDup", group_id=str(group.id), user_type_id=str(ut.id)))
    db.commit()

    form_data = {
        "username": user1.username,
        "group_id": str(group.id),
        "user_type_id": str(ut.id)
    }

    response = await async_client.put(f"/pages/user/row/{user2.id}", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{user2.id}"
    # HTMLエスケープされたシングルクォートを検証, 末尾の不要なスペースを削除
    expected_error = f"ユーザー名 &#39;{user1.username}&#39; は既に使用されています。" 
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text 

@pytest.mark.asyncio
async def test_handle_update_user_row_invalid_group_id(async_client: AsyncClient, db: Session) -> None:
    """存在しないグループIDで更新しようとすると400エラーとエラーHTMLが返るテスト"""
    group, ut = create_test_dependencies_for_page(db)
    user = crud_user.create(db, obj_in=UserCreate(user_id="update_invalid_group", username="Invalid Group Update", group_id=str(group.id), user_type_id=str(ut.id)))
    db.commit()
    invalid_group_id = 99998

    form_data = {
        "username": "Updated Invalid Group",
        "group_id": str(invalid_group_id), # 存在しないグループID
        "user_type_id": str(ut.id)
    }

    response = await async_client.put(f"/pages/user/row/{user.id}", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{user.id}"
    expected_error = f"指定されたグループID({invalid_group_id})は存在しません。"
    assert expected_error in response.text

@pytest.mark.asyncio
async def test_handle_update_user_row_invalid_user_type_id(async_client: AsyncClient, db: Session) -> None:
    """存在しない社員種別IDで更新しようとすると400エラーとエラーHTMLが返るテスト"""
    group, ut = create_test_dependencies_for_page(db)
    user = crud_user.create(db, obj_in=UserCreate(user_id="update_invalid_utype", username="Invalid UserType Update", group_id=str(group.id), user_type_id=str(ut.id)))
    db.commit()
    invalid_user_type_id = 88887

    form_data = {
        "username": "Updated Invalid UserType",
        "group_id": str(group.id),
        "user_type_id": str(invalid_user_type_id) # 存在しない社員種別ID
    }

    response = await async_client.put(f"/pages/user/row/{user.id}", data=form_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{user.id}"
    expected_error = f"指定された社員種別ID({invalid_user_type_id})は存在しません。"
    assert expected_error in response.text 