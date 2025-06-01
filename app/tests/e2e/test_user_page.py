from playwright.sync_api import Page, expect
import time
import re
from urllib.parse import quote
import contextlib # finally でのエラー抑制用

# ヘルパー関数：テストに必要なグループ名と社員種別名を取得
def get_required_data(page: Page) -> tuple[str, str, str, str]:
    """ユーザー追加/編集に必要なグループ名と社員種別名を取得"""
    page.goto("http://localhost:8000/user")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
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

def create_test_group_ui(page: Page, group_name: str) -> int:
    """UI操作でテスト用グループを作成し、そのIDを返す"""
    page.goto("http://localhost:8000/group")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("グループ追加")').click()
    add_modal = page.locator("#add-group")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-group-name').fill(group_name)
    add_modal.locator('button[form="add-group-form"]').click()
    # モーダルが閉じることを確認
    expect(add_modal).to_be_hidden(timeout=500)
    # テーブルに追加された行を見つける (リロード待機)
    row_locator = page.locator(f'#group-table-body tr:has-text("{group_name}")')
    expect(row_locator).to_be_visible(timeout=500)
    row_id = row_locator.get_attribute('id')
    assert row_id and row_id.startswith("group-row-"), f"Could not find row or ID for group: {group_name}"
    group_id = int(row_id.split('-')[-1])
    print(f"Created test group: {group_name} (ID: {group_id})")
    return group_id

def delete_test_group_ui(page: Page, group_id: int) -> None:
    """UI操作で指定されたIDのグループを削除する"""
    print(f"Attempting to delete group ID: {group_id}")
    page.goto("http://localhost:8000/group")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    row_locator = page.locator(f"#group-row-{group_id}")
    # 要素が存在しない場合は何もしない (既に削除されているか、作成失敗)
    if not row_locator.is_visible():
        print(f"Group row {group_id} not visible, skipping deletion.")
        return
    # 行内の削除ボタンをクリック
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
    # 削除確認モーダル
    delete_modal = page.locator('dialog:has(h3:has-text("グループの削除"))')
    expect(delete_modal).to_be_visible()
    delete_modal.locator('button:has-text("削除")').click()
    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=500)
    # 行が消えるのを待つ
    expect(row_locator).not_to_be_visible(timeout=500)
    print(f"Deleted test group ID: {group_id}")

def create_test_user_type_ui(page: Page, user_type_name: str) -> int:
    """UI操作でテスト用社員種別を作成し、そのIDを返す"""
    page.goto("http://localhost:8000/user_type")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("社員種別追加")').click()
    add_modal = page.locator("#add-user-type")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-user-type-name').fill(user_type_name)
    add_modal.locator('button[form="add-user-type-form"]').click()
    # モーダルが閉じることを確認
    expect(add_modal).to_be_hidden(timeout=500)
    # テーブルに追加された行を見つける (リロード待機)
    row_locator = page.locator(f'#user-type-table-body tr:has-text("{user_type_name}")')
    expect(row_locator).to_be_visible(timeout=500)
    row_id = row_locator.get_attribute('id')
    assert row_id and row_id.startswith("user-type-row-"), f"Could not find row or ID for user type: {user_type_name}"
    user_type_id = int(row_id.split('-')[-1])
    print(f"Created test user type: {user_type_name} (ID: {user_type_id})")
    return user_type_id

def delete_test_user_type_ui(page: Page, user_type_id: int) -> None:
    """UI操作で指定されたIDの社員種別を削除する"""
    print(f"Attempting to delete user type ID: {user_type_id}")
    page.goto("http://localhost:8000/user_type")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    row_locator = page.locator(f"#user-type-row-{user_type_id}")
    if not row_locator.is_visible():
        print(f"User type row {user_type_id} not visible, skipping deletion.")
        return
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
    delete_modal = page.locator('dialog:has(h3:has-text("社員種別の削除"))')
    expect(delete_modal).to_be_visible()
    delete_modal.locator('button:has-text("削除")').click()
    expect(delete_modal).to_be_hidden(timeout=500)
    expect(row_locator).not_to_be_visible(timeout=500)
    print(f"Deleted test user type ID: {user_type_id}")

def delete_test_user_ui(page: Page, user_id: str) -> None:
    """UI操作で指定されたIDの社員を削除する"""
    print(f"Attempting to delete user ID: {user_id}")
    page.goto("http://localhost:8000/user") # ユーザーページへ移動
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    row_locator = page.locator(f'#user-row-{user_id}')
    if not row_locator.is_visible():
        print(f"User row {user_id} not visible, skipping deletion.")
        return
    
    # 削除ボタンをクリック
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
    
    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator(f"#user-delete-modal-{user_id}")
    expect(delete_modal).to_be_visible()
    
    # 削除ボタンをクリック
    delete_modal.locator('button.btn-error').click()
    
    # 削除が完了するまで待機
    expect(row_locator).not_to_be_visible(timeout=500)
    print(f"Deleted test user ID: {user_id}")

def test_add_new_user(page: Page) -> None:
    """社員管理ページで新しい社員を追加するテスト (依存データ作成・削除込み)"""
    timestamp = int(time.time())
    group_name = f"テストグループ_追加_{timestamp}"
    user_type_name = f"テスト種別_追加_{timestamp}"
    unique_username = f"テスト社員_追加_{timestamp}"
    unique_user_id = f"add{timestamp}"

    created_group_id = None
    created_user_type_id = None

    try:
        # 1. 依存データ作成
        created_group_id = create_test_group_ui(page, group_name)
        created_user_type_id = create_test_user_type_ui(page, user_type_name)

        # 2. 社員追加テスト本体
        page.goto("http://localhost:8000/user")
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.locator('button:has-text("社員追加")').click()
        add_modal_locator = page.locator("#user-modal-new")
        expect(add_modal_locator).to_be_visible()
        add_modal_locator.locator('input[name="username"]').fill(unique_username)
        add_modal_locator.locator('input[name="id"]').fill(unique_user_id)
        # 作成したグループと種別を選択
        add_modal_locator.locator('select[name="group_id"]').select_option(value=str(created_group_id))
        add_modal_locator.locator('select[name="user_type_id"]').select_option(value=str(created_user_type_id))
        add_modal_locator.locator('button[form="user-modal-new-form"]').click()

        # 確認
        encoded_group_name = quote(group_name)
        group_table_body_selector = f'tbody[id="user-table-body-{encoded_group_name}"]'
        expected_text = f"{unique_username} ({unique_user_id})"
        expect(page.locator(group_table_body_selector)).to_contain_text(expected_text, timeout=500)

    finally:
        # 3. クリーンアップ (エラーが発生しても実行)
        # 社員を削除 (作成されていれば)
        with contextlib.suppress(Exception): # クリーンアップ中のエラーは握りつぶす
            delete_test_user_ui(page, unique_user_id)
        # 社員種別を削除
        if created_user_type_id is not None:
            with contextlib.suppress(Exception):
                delete_test_user_type_ui(page, created_user_type_id)
        # グループを削除
        if created_group_id is not None:
            with contextlib.suppress(Exception):
                delete_test_group_ui(page, created_group_id)

def test_edit_user(page: Page) -> None:
    """既存の社員情報を編集するテスト (依存データ作成・削除込み)"""
    timestamp = int(time.time())
    # 編集前後のグループ/種別
    initial_group_name = f"編集前グループ_{timestamp}"
    initial_user_type_name = f"編集前種別_{timestamp}"
    new_group_name = f"編集後グループ_{timestamp}" # グループ変更もテスト
    # ユーザー情報
    initial_username = f"編集前社員_{timestamp}"
    initial_user_id = f"edit{timestamp}"
    new_username = f"編集済_{initial_username}"

    initial_group_id = None
    initial_user_type_id = None
    new_group_id = None
    created_user_id = None # 作成したユーザーIDを追跡

    try:
        # 1. 依存データ作成 (編集前/後)
        initial_group_id = create_test_group_ui(page, initial_group_name)
        initial_user_type_id = create_test_user_type_ui(page, initial_user_type_name)
        new_group_id = create_test_group_ui(page, new_group_name) # 編集後のグループも作成

        # 2. テスト用社員作成 (編集対象)
        page.goto("http://localhost:8000/user")
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.locator('button:has-text("社員追加")').click()
        add_modal = page.locator("#user-modal-new")
        expect(add_modal).to_be_visible()
        add_modal.locator('input[name="username"]').fill(initial_username)
        add_modal.locator('input[name="id"]').fill(initial_user_id)
        add_modal.locator('select[name="group_id"]').select_option(value=str(initial_group_id))
        add_modal.locator('select[name="user_type_id"]').select_option(value=str(initial_user_type_id))
        add_modal.locator('button[form="user-modal-new-form"]').click()
        created_user_id = initial_user_id # 追跡用に保存

        # 追加確認 (リロード待機)
        encoded_initial_group_name = quote(initial_group_name)
        initial_group_table_selector = f'tbody[id="user-table-body-{encoded_initial_group_name}"]'
        expect(page.locator(initial_group_table_selector)).to_contain_text(f"{initial_username} ({initial_user_id})", timeout=500)

        # 3. 編集操作
        row_locator = page.locator(f'#user-row-{initial_user_id}')
        expect(row_locator).to_be_visible()
        row_locator.locator('button:has-text("編集")').click()
        edit_modal_locator = page.locator(f"#user-modal-{initial_user_id}")
        expect(edit_modal_locator).to_be_visible()
        # 値の確認
        expect(edit_modal_locator.locator('input[name="username"]')).to_have_value(initial_username, timeout=500)
        expect(edit_modal_locator.locator('select[name="group_id"]')).to_have_value(str(initial_group_id))
        expect(edit_modal_locator.locator('select[name="user_type_id"]')).to_have_value(str(initial_user_type_id))
        # 値の変更 (名前とグループ)
        edit_modal_locator.locator('input[name="username"]').fill(new_username)
        edit_modal_locator.locator('select[name="group_id"]').select_option(value=str(new_group_id))
        edit_modal_locator.locator('.modal-action button.btn-neutral').click()

        # 4. 更新確認
        # 更新後のグループテーブルに移動していることを確認
        encoded_new_group_name = quote(new_group_name)
        new_group_table_selector = f'tbody[id="user-table-body-{encoded_new_group_name}"]'
        updated_row_locator_in_new_table = page.locator(new_group_table_selector).locator(f'#user-row-{initial_user_id}')
        expect(updated_row_locator_in_new_table).to_be_visible(timeout=500)
        # 更新された名前が表示されていることを確認
        expect(updated_row_locator_in_new_table.locator('td').first).to_contain_text(f"{new_username} ({initial_user_id})")
        # 古いグループテーブルに行が存在しないことを確認
        expect(page.locator(initial_group_table_selector).locator(f'#user-row-{initial_user_id}')).not_to_be_visible()

    finally:
        # 5. クリーンアップ
        if created_user_id:
            with contextlib.suppress(Exception):
                delete_test_user_ui(page, created_user_id)
        # 作成したグループ、社員種別を削除
        if new_group_id:
            with contextlib.suppress(Exception):
                delete_test_group_ui(page, new_group_id)
        if initial_user_type_id:
             with contextlib.suppress(Exception):
                delete_test_user_type_ui(page, initial_user_type_id)
        if initial_group_id:
            with contextlib.suppress(Exception):
                delete_test_group_ui(page, initial_group_id)

def test_delete_user(page: Page) -> None:
    """既存の社員を削除するテスト (依存データ作成・削除込み)"""
    timestamp = int(time.time())
    group_name = f"削除用グループ_{timestamp}"
    user_type_name = f"削除用種別_{timestamp}"
    username_to_delete = f"削除用社員_{timestamp}"
    user_id_to_delete = f"del{timestamp}"

    created_group_id = None
    created_user_type_id = None
    created_user_id = None # 追跡用

    try:
        # 1. 依存データ作成
        created_group_id = create_test_group_ui(page, group_name)
        created_user_type_id = create_test_user_type_ui(page, user_type_name)

        # 2. テスト用社員作成 (削除対象)
        page.goto("http://localhost:8000/user")
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
        page.locator('button:has-text("社員追加")').click()
        add_modal = page.locator("#user-modal-new")
        expect(add_modal).to_be_visible()
        add_modal.locator('input[name="username"]').fill(username_to_delete)
        add_modal.locator('input[name="id"]').fill(user_id_to_delete)
        add_modal.locator('select[name="group_id"]').select_option(value=str(created_group_id))
        add_modal.locator('select[name="user_type_id"]').select_option(value=str(created_user_type_id))
        add_modal.locator('button[form="user-modal-new-form"]').click()
        created_user_id = user_id_to_delete # 追跡

        # 追加確認
        encoded_group_name = quote(group_name)
        group_table_body_selector = f'tbody[id="user-table-body-{encoded_group_name}"]'
        expect(page.locator(group_table_body_selector)).to_contain_text(f"{username_to_delete} ({user_id_to_delete})", timeout=500)

        # 3. 削除操作
        row_locator = page.locator(f'#user-row-{user_id_to_delete}')
        expect(row_locator).to_be_visible()
        row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
        delete_modal_locator = page.locator(f"#user-delete-modal-{user_id_to_delete}")
        expect(delete_modal_locator).to_be_visible()
        delete_modal_locator.locator('button.btn-error').click()

        # 4. 削除確認
        expect(row_locator).not_to_be_visible(timeout=500)
        created_user_id = None # 削除されたので追跡不要

    finally:
        # 5. クリーンアップ
        if created_user_id: # もし削除テスト自体が失敗した場合に備える
             with contextlib.suppress(Exception):
                delete_test_user_ui(page, created_user_id)
        if created_user_type_id:
             with contextlib.suppress(Exception):
                delete_test_user_type_ui(page, created_user_type_id)
        if created_group_id:
            with contextlib.suppress(Exception):
                delete_test_group_ui(page, created_group_id) 