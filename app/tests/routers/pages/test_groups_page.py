import pytest
from httpx import AsyncClient
from fastapi import status, FastAPI
from sqlalchemy.orm import Session
import re # 正規表現モジュールをインポート
import json

# モデル、スキーマ、CRUD をインポート
from app.models.group import Group
from app.schemas.group import GroupCreate
from app.crud.group import group as crud_group


@pytest.mark.asyncio
async def test_read_groups_page(async_client: AsyncClient, db: Session) -> None:
    """グループ管理ページ (GET /groups) が正常に取得でき、データが表示されることをテスト"""
    # Test data setup
    group1 = crud_group.create(db, obj_in=GroupCreate(name="Group Page Test A"))
    group2 = crud_group.create(db, obj_in=GroupCreate(name="Group Page Test B"))
    db.commit()

    response = await async_client.get("/groups")
    assert response.status_code == status.HTTP_200_OK
    html = response.text
    assert "<title>Sokora - グループ管理</title>" in html

    # グループデータがテーブルに表示されていることを確認
    assert re.search(rf'<tr\s+.*?id="group-row-{group1.id}".*?>', html) is not None
    assert re.search(rf'<span\s+id="group-name-{group1.id}">{re.escape(str(group1.name))}<\/span>', html) is not None
    assert re.search(rf'<tr\s+.*?id="group-row-{group2.id}".*?>', html) is not None
    assert re.search(rf'<span\s+id="group-name-{group2.id}">{re.escape(str(group2.name))}<\/span>', html) is not None

    # 編集ボタンの hx-get 属性を確認
    assert f'hx-get="/pages/group/edit/{group1.id}"' in html
    # 削除ボタンの正しい endpoint_url (hx-delete 属性の値) を確認
    # delete_confirm_modal マクロ内で hx-delete が設定されるため、その呼び出し部分を間接的に確認
    # 正確には、モーダル内のボタンの属性を確認する必要があるが、ここではテンプレート呼び出しの引数を確認
    expected_delete_url_g1 = f"/api/groups/{group1.id}"
    # delete_confirm_modal 呼び出し時の endpoint_url 引数を確認 (正規表現または文字列検索)
    # 例: delete_confirm_modal(..., '/api/groups/' + group.id|string, ...)
    # 修正: モーダル内の削除ボタンの hx-delete 属性を文字列検索で確認
    # モーダルは x-show で初期非表示だが HTML には含まれるはず
    delete_button_html_g1 = f'hx-delete="{expected_delete_url_g1}"'
    assert delete_button_html_g1 in html, f"Delete button with correct hx-delete for group {group1.id} not found"


@pytest.mark.asyncio
async def test_get_group_edit_form_success(async_client: AsyncClient, db: Session) -> None:
    """グループ編集フォームが正常に取得できることをテスト"""
    group = crud_group.create(db, obj_in=GroupCreate(name="Edit Group Form Test"))
    db.commit()

    response = await async_client.get(f"/pages/group/edit/{group.id}")
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    # フォームの基本的な属性を確認
    assert f'id="edit-form-group-{group.id}"' in html
    assert f'hx-put="/pages/group/row/{group.id}"' in html
    assert 'hx-indicator="#loading-indicator"' in html

    # グループ名 input の存在と value を確認 (より厳密に)
    assert re.search(r'<input[^>]*name="name"[^>]*>', html) is not None, "Input field for name not found"
    assert f'value="{group.name}"' in html, "Input field does not contain correct value"

    # 保存ボタンとキャンセルボタンの存在を確認
    assert re.search(r'<button\s+type="submit".*?>保存<\/button>', html) is not None
    assert re.search(r'<button\s+type="button".*?@click="showEditModal\s*=\s*false".*?>キャンセル<\/button>', html) is not None


@pytest.mark.asyncio
async def test_get_group_edit_form_not_found(async_client: AsyncClient) -> None:
    """存在しないグループIDで編集フォームを取得しようとすると404になることをテスト"""
    response = await async_client.get("/pages/group/edit/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

# --- POST /pages/group/row --- 

@pytest.mark.asyncio
async def test_handle_create_group_row_success(async_client: AsyncClient, db: Session) -> None:
    """グループが正常に作成され、対応する行のHTMLが返されることをテスト"""
    group_name = "Create Group Row Test"
    form_data = {"name": group_name}

    response = await async_client.post("/pages/group/row", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    # Find the created group to get its ID
    db_group = db.query(Group).filter(Group.name == group_name).first()
    assert db_group is not None
    group_id = db_group.id

    assert f'id="group-row-{group_id}"' in html
    assert f'<span id="group-name-{group_id}">{group_name}</span>' in html

    # Check HX-Trigger header for success message and refresh
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert "showMessage" in trigger_data
    assert f"グループ {group_name} を追加しました" in trigger_data["showMessage"]
    assert trigger_data.get("refreshPage") is True

@pytest.mark.asyncio
async def test_handle_create_group_row_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """重複するグループ名で作成しようとすると400エラーとエラーHTMLが返るテスト"""
    existing_name = "Duplicate Create Name"
    crud_group.create(db, obj_in=GroupCreate(name=existing_name))
    db.commit()

    form_data = {"name": existing_name}
    response = await async_client.post("/pages/group/row", data=form_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == "#add-form-error"
    expected_error = "このグループ名は既に存在します"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text
    # Check HX-Trigger header for error message
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert trigger_data.get("showMessage") == expected_error
    assert trigger_data.get("isError") is True

# --- PUT /pages/group/row/{group_id} ---

@pytest.mark.asyncio
async def test_handle_update_group_row_success(async_client: AsyncClient, db: Session) -> None:
    """グループ情報が正常に更新され、対応する行のHTMLが返されることをテスト"""
    group_to_update = crud_group.create(db, obj_in=GroupCreate(name="Original Update Name"))
    db.commit()
    group_id = group_to_update.id

    updated_name = "Successfully Updated Name"
    form_data = {"name": updated_name}

    response = await async_client.put(f"/pages/group/row/{group_id}", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    html = response.text

    assert f'id="group-row-{group_id}"' in html
    assert f'<span id="group-name-{group_id}">{updated_name}</span>' in html

    # Check HX-Trigger header for success message and refresh
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert "showMessage" in trigger_data
    assert f"グループ {updated_name} を更新しました" in trigger_data["showMessage"]
    assert trigger_data.get("refreshPage") is True

    # DB確認
    db.refresh(group_to_update)
    assert group_to_update.name == updated_name

@pytest.mark.asyncio
async def test_handle_update_group_row_duplicate_name(async_client: AsyncClient, db: Session) -> None:
    """他のグループと重複するグループ名で更新しようとすると400エラーになるテスト"""
    group1 = crud_group.create(db, obj_in=GroupCreate(name="Update Group 1"))
    group2 = crud_group.create(db, obj_in=GroupCreate(name="Existing Group Name"))
    db.commit()
    group1_id = group1.id
    existing_name = group2.name

    form_data = {"name": existing_name}
    response = await async_client.put(f"/pages/group/row/{group1_id}", data=form_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "HX-Retarget" in response.headers
    assert response.headers["HX-Retarget"] == f"#edit-form-error-{group1_id}"
    expected_error = "このグループ名は既に使用されています"
    assert expected_error in response.text
    assert '<div id="form-error"' in response.text
    # Check HX-Trigger header for error message
    assert "HX-Trigger" in response.headers
    trigger_data = json.loads(response.headers["HX-Trigger"])
    assert trigger_data.get("showMessage") == expected_error
    assert trigger_data.get("isError") is True

@pytest.mark.asyncio
async def test_handle_update_group_row_not_found(async_client: AsyncClient) -> None:
    """存在しないグループIDで更新しようとすると404エラーになるテスト"""
    form_data = {"name": "Update Non Existent"}
    response = await async_client.put("/pages/group/row/99999", data=form_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND 