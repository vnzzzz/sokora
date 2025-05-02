from playwright.sync_api import Page, expect
import time
import re

def test_add_new_user_type(page: Page) -> None:
    """社員種別管理ページで新しい社員種別を追加するテスト"""
    timestamp = int(time.time())
    unique_user_type_name = f"テスト種別_{timestamp}"

    page.goto("http://localhost:8000/user_types")

    # 「社員種別追加」ボタンをクリック
    page.locator('button:has-text("社員種別追加")').click()

    # 追加モーダルが表示されるのを待機 (IDで特定)
    add_modal_locator = page.locator("#add-user-type-modal")
    expect(add_modal_locator).to_be_visible()

    # 情報を入力
    add_modal_locator.locator('#add-user-type-name').fill(unique_user_type_name)

    # 「追加」ボタンをクリック (モーダル内のsubmit)
    add_modal_locator.locator('button[type="submit"]').click()

    # ページがリロードされ、テーブルに新しい社員種別が表示されるのを待機・確認
    table_body_selector = "#user-type-table-body"
    expect(page.locator(table_body_selector)).to_contain_text(unique_user_type_name, timeout=10000) # リロード待機

    # --- テストデータ削除 ---
    row_locator = page.locator(f'#user-type-table-body tr:has-text("{unique_user_type_name}")')
    expect(row_locator).to_be_visible()
    row_id = row_locator.get_attribute('id')
    assert row_id is not None
    user_type_id_str = row_id.split('-')[-1]
    assert user_type_id_str.isdigit()
    user_type_id = int(user_type_id_str)
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
    delete_form_locator = page.locator(f"#delete-form-{user_type_id}")
    expect(delete_form_locator).to_be_visible()
    delete_form_locator.locator('button[hx-delete]').click()
    expect(row_locator).not_to_be_visible(timeout=10000)
    # -----------------------

def test_edit_user_type(page: Page) -> None:
    """既存の社員種別を編集するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    timestamp = int(time.time())
    initial_name = f"編集前種別_{timestamp}"
    new_name = f"編集済_{initial_name}"

    page.goto("http://localhost:8000/user_types")
    page.locator('button:has-text("社員種別追加")').click()
    add_modal = page.locator("#add-user-type-modal")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-user-type-name').fill(initial_name)
    add_modal.locator('button[type="submit"]').click()
    expect(page.locator("#user-type-table-body")).to_contain_text(initial_name, timeout=10000)
    # ------------------------------------

    # 編集対象の行を見つける (テキストで特定)
    row_locator = page.locator(f'#user-type-table-body tr:has-text("{initial_name}")')
    expect(row_locator).to_be_visible()
    # 行 ID から user_type_id を取得 (例: 'user-type-row-5' -> 5)
    row_id = row_locator.get_attribute('id')
    assert row_id is not None, f"Row ID attribute not found for row with text: {initial_name}"
    user_type_id_str = row_id.split('-')[-1]
    assert user_type_id_str.isdigit(), "Failed to extract user_type ID from row ID"
    user_type_id = int(user_type_id_str)

    # その行の中の編集ボタンをクリック
    row_locator.locator('button:has-text("編集")').click()

    # 編集モーダルが表示されるのを待機 (フォームIDで特定)
    edit_form_locator = page.locator(f"#edit-form-user-type-{user_type_id}")
    expect(edit_form_locator).to_be_visible()
    # HTMXでロードされるコンテンツ内の input を待機
    expect(edit_form_locator.locator('input[name="name"]')).to_have_value(initial_name, timeout=5000)

    # 新しい名前を入力
    edit_form_locator.locator('input[name="name"]').fill(new_name)

    # 「保存」ボタンをクリック
    edit_form_locator.locator('button[type="submit"]:has-text("保存")').click()

    # ページがリロードされ、行が更新されるのを待機・確認
    updated_row_locator = page.locator(f"#user-type-row-{user_type_id}")
    expect(updated_row_locator.locator('td').first).to_have_text(new_name, timeout=10000)

    # --- テストデータ削除 ---
    row_locator = page.locator(f'#user-type-table-body tr:has-text("{new_name}")')
    expect(row_locator).to_be_visible()
    row_id = row_locator.get_attribute('id')
    assert row_id is not None
    user_type_id_str = row_id.split('-')[-1]
    assert user_type_id_str.isdigit()
    user_type_id = int(user_type_id_str) # 再取得
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()
    delete_form_locator = page.locator(f"#delete-form-{user_type_id}")
    expect(delete_form_locator).to_be_visible()
    delete_form_locator.locator('button[hx-delete]').click()
    expect(row_locator).not_to_be_visible(timeout=10000)
    # -----------------------

def test_delete_user_type(page: Page) -> None:
    """既存の社員種別を削除するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    timestamp = int(time.time())
    name_to_delete = f"削除用種別_{timestamp}"

    page.goto("http://localhost:8000/user_types")
    page.locator('button:has-text("社員種別追加")').click()
    add_modal = page.locator("#add-user-type-modal")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-user-type-name').fill(name_to_delete)
    add_modal.locator('button[type="submit"]').click()
    expect(page.locator("#user-type-table-body")).to_contain_text(name_to_delete, timeout=10000)
    # ------------------------------------

    # 削除対象の行を見つける (テキストで特定)
    row_locator = page.locator(f'#user-type-table-body tr:has-text("{name_to_delete}")')
    expect(row_locator).to_be_visible()
    # 行 ID から user_type_id を取得
    row_id = row_locator.get_attribute('id')
    assert row_id is not None, f"Row ID attribute not found for row with text: {name_to_delete}"
    user_type_id_str = row_id.split('-')[-1]
    assert user_type_id_str.isdigit(), "Failed to extract user_type ID from row ID"
    user_type_id = int(user_type_id_str)

    # 行内の削除ボタンをクリック (詳細セレクタ)
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()

    # 削除確認モーダル内のフォームが表示されるのを待機
    delete_form_locator = page.locator(f"#delete-form-{user_type_id}")
    expect(delete_form_locator).to_be_visible()

    # モーダル内の「削除」ボタン (APIエンドポイントを叩くボタン) をクリック
    delete_form_locator.locator('button[hx-delete]').click()

    # API 呼び出し -> JS でリロードされるのを待機し、行が消えていることを確認
    expect(row_locator).not_to_be_visible(timeout=10000) 