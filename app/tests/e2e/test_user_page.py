from playwright.sync_api import Page, expect
import time
import re
from urllib.parse import quote

# ヘルパー関数：テストに必要なグループ名と社員種別名を取得
def get_required_data(page: Page) -> tuple[str, str, str, str]:
    """ユーザー追加/編集に必要なグループ名と社員種別名を取得"""
    page.goto("http://localhost:8000/user")
    page.locator('button:has-text("社員追加")').click()
    add_modal_locator = page.locator("form#add-user-form").locator("..") # form の親 (modal-box)
    expect(add_modal_locator).to_be_visible()

    # グループ選択肢から最初の有効なオプションを取得
    group_select = add_modal_locator.locator("#add-group-id")
    first_group_option = group_select.locator("option:not([value=''])").first
    # expect(first_group_option).to_be_visible() # option の可視性チェックは不要
    group_name = first_group_option.inner_text()
    group_id = first_group_option.get_attribute("value")
    assert group_id is not None and group_id != "", "Failed to get a valid group ID"

    # 社員種別選択肢から最初の有効なオプションを取得
    user_type_select = add_modal_locator.locator("#add-user-type-id")
    first_user_type_option = user_type_select.locator("option:not([value=''])").first
    # expect(first_user_type_option).to_be_visible() # option の可視性チェックは不要
    user_type_name = first_user_type_option.inner_text()
    user_type_id = first_user_type_option.get_attribute("value")
    assert user_type_id is not None and user_type_id != "", "Failed to get a valid user type ID"

    # モーダルを閉じる
    add_modal_locator.locator('button:has-text("キャンセル")').click()
    expect(add_modal_locator).not_to_be_visible()

    print(f"Using Group: {group_name} (ID: {group_id}), User Type: {user_type_name} (ID: {user_type_id})") # デバッグ用
    return group_name, group_id, user_type_name, user_type_id


def test_add_new_user(page: Page) -> None:
    """社員管理ページで新しい社員を追加するテスト"""
    group_name, group_id, _, user_type_id = get_required_data(page)
    timestamp = int(time.time())
    unique_username = f"テスト社員_{timestamp}"
    unique_user_id = f"test{timestamp}"

    page.goto("http://localhost:8000/user")
    page.locator('button:has-text("社員追加")').click()
    add_modal_locator = page.locator("form#add-user-form").locator("..")
    expect(add_modal_locator).to_be_visible()
    add_modal_locator.locator('#add-username').fill(unique_username)
    add_modal_locator.locator('#add-user-id').fill(unique_user_id)
    add_modal_locator.locator('#add-group-id').select_option(label=group_name)
    add_modal_locator.locator('#add-user-type-id').select_option(value=user_type_id)
    add_modal_locator.locator('button[type="submit"]').click()

    # グループ名を URL エンコードして属性セレクタを作成
    encoded_group_name = quote(group_name)
    group_table_body_selector = f'tbody[id="user-table-body-{encoded_group_name}"]'
    expected_text = f"{unique_username} ({unique_user_id})"
    expect(page.locator(group_table_body_selector)).to_contain_text(expected_text, timeout=10000)


def test_edit_user(page: Page) -> None:
    """既存の社員情報を編集するテスト"""
    group_name, group_id, _, user_type_id = get_required_data(page)
    timestamp = int(time.time())
    initial_username = f"編集前社員_{timestamp}"
    initial_user_id = f"edit{timestamp}"
    new_username = f"編集済_{initial_username}"

    page.goto("http://localhost:8000/user")
    page.locator('button:has-text("社員追加")').click()
    add_modal = page.locator("form#add-user-form").locator("..")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-username').fill(initial_username)
    add_modal.locator('#add-user-id').fill(initial_user_id)
    add_modal.locator('#add-group-id').select_option(value=group_id)
    add_modal.locator('#add-user-type-id').select_option(value=user_type_id)
    add_modal.locator('button[type="submit"]').click()

    # グループ名を URL エンコードして属性セレクタを作成
    encoded_group_name = quote(group_name)
    group_table_body_selector = f'tbody[id="user-table-body-{encoded_group_name}"]'
    expected_initial_text = f"{initial_username} ({initial_user_id})"
    expect(page.locator(group_table_body_selector)).to_contain_text(expected_initial_text, timeout=10000)

    row_locator = page.locator(f'#user-row-{initial_user_id}')
    expect(row_locator).to_be_visible()
    row_locator.locator('button:has-text("編集")').click()
    edit_form_locator = page.locator(f"#edit-form-{initial_user_id}")
    expect(edit_form_locator).to_be_visible()
    expect(edit_form_locator.locator('input[name="username"]')).to_have_value(initial_username, timeout=5000)
    expect(edit_form_locator.locator('select[name="group_id"]')).to_have_value(group_id)
    expect(edit_form_locator.locator('select[name="user_type_id"]')).to_have_value(user_type_id)
    edit_form_locator.locator('input[name="username"]').fill(new_username)
    edit_form_locator.locator('button[type="submit"]:has-text("保存")').click()

    updated_row_locator = page.locator(f'#user-row-{initial_user_id}')
    expected_updated_text = f"{new_username} ({initial_user_id})"
    expect(updated_row_locator.locator('td').first).to_contain_text(expected_updated_text, timeout=10000)

def test_delete_user(page: Page) -> None:
    """既存の社員を削除するテスト"""
    group_name, group_id, _, user_type_id = get_required_data(page)
    timestamp = int(time.time())
    username_to_delete = f"削除用社員_{timestamp}"
    user_id_to_delete = f"del{timestamp}"

    page.goto("http://localhost:8000/user")
    page.locator('button:has-text("社員追加")').click()
    add_modal = page.locator("form#add-user-form").locator("..")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-username').fill(username_to_delete)
    add_modal.locator('#add-user-id').fill(user_id_to_delete)
    add_modal.locator('#add-group-id').select_option(value=group_id)
    add_modal.locator('#add-user-type-id').select_option(value=user_type_id)
    add_modal.locator('button[type="submit"]').click()

    # グループ名を URL エンコードして属性セレクタを作成
    encoded_group_name = quote(group_name)
    group_table_body_selector = f'tbody[id="user-table-body-{encoded_group_name}"]'
    expected_initial_text = f"{username_to_delete} ({user_id_to_delete})"
    expect(page.locator(group_table_body_selector)).to_contain_text(expected_initial_text, timeout=10000)

    row_locator = page.locator(f'#user-row-{user_id_to_delete}')
    expect(row_locator).to_be_visible()
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
    delete_form_locator = page.locator(f"#delete-form-{user_id_to_delete}")
    expect(delete_form_locator).to_be_visible()
    delete_form_locator.locator('button[hx-delete]').click()
    expect(row_locator).not_to_be_visible(timeout=10000) 