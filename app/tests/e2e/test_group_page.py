# app/tests/e2e/test_group_page.py

from playwright.sync_api import Page, expect
import time
import re

def test_add_new_group(page: Page) -> None:
    """グループ管理ページで新しいグループを追加するテスト"""
    timestamp = int(time.time())
    unique_group_name = f"テストグループ_{timestamp}"

    page.goto("http://localhost:8000/group")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 「グループ追加」ボタンをクリック
    page.locator('button:has-text("グループ追加")').click()

    # 追加モーダルが表示されるのを待機 (IDで特定)
    add_modal_locator = page.locator("#add-group")
    expect(add_modal_locator).to_be_visible()

    # グループ名を入力
    add_modal_locator.locator('#add-group-name').fill(unique_group_name)

    # 「登録」ボタンをクリック
    add_modal_locator.locator('button[form="add-group-form"]').click()

    # モーダルが閉じることを確認（少し待機）
    expect(add_modal_locator).to_be_hidden(timeout=2000)

    # 新しく追加されたグループが表に表示されているかを確認
    expect(page.locator('#group-table-body')).to_contain_text(unique_group_name)

    # --- テストデータ削除 ---
    row_locator = page.locator(f'#group-table-body tr:has-text("{unique_group_name}")')
    expect(row_locator).to_be_visible()
    
    # 削除ボタンをクリック
    delete_button = row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator('dialog:has(h3:has-text("グループの削除"))')
    expect(delete_modal).to_be_visible()
    
    # 削除ボタンをクリック
    delete_modal.locator('button:has-text("削除")').click()
    
    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=2000)
    
    # 削除したグループが表から消えていることを確認
    expect(page.locator('#group-table-body')).not_to_contain_text(unique_group_name)
    # -----------------------

def test_edit_group(page: Page) -> None:
    """既存のグループを編集するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    timestamp = int(time.time())
    initial_name = f"編集前グループ_{timestamp}"
    new_name = f"編集済_{initial_name}"

    page.goto("http://localhost:8000/group")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("グループ追加")').click()
    add_modal = page.locator("#add-group")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-group-name').fill(initial_name)
    add_modal.locator('button[form="add-group-form"]').click()
    expect(add_modal).to_be_hidden()

    # テーブルに追加されたグループが表示されていることを確認
    expect(page.locator('#group-table-body')).to_contain_text(initial_name)

    # 編集ボタンをクリックしてモーダルを開く
    edit_button = page.locator('tr').filter(has_text=initial_name).locator('button:has-text("編集")')
    edit_button.click()

    # 編集モーダルが表示されるのを待機
    edit_modal = page.locator('dialog:has(h3:has-text("グループ編集"))')
    expect(edit_modal).to_be_visible()

    # グループ名を変更
    edit_modal.locator('input[name="name"]').fill(new_name)

    # 「更新」ボタンをクリック
    edit_modal.locator('.modal-action button.btn-neutral').click()

    # モーダルが閉じることを確認
    expect(edit_modal).to_be_hidden(timeout=2000)

    # HTMX更新完了まで少し待機
    page.wait_for_timeout(1000)

    # 更新後のグループ名が表に表示されているかを確認
    updated_row = page.locator(f'#group-table-body tr:has-text("{new_name}")')
    expect(updated_row).to_be_visible()
    
    # 古い名前だけを含む行が存在しないことを確認（編集済み_を含まない古い名前）
    old_only_row = page.locator(f'#group-table-body tr:has-text("{initial_name}"):not(:has-text("{new_name}"))')
    expect(old_only_row).not_to_be_visible()

    # --- テストデータ削除 ---
    row_locator = page.locator(f'#group-table-body tr:has-text("{new_name}")')
    expect(row_locator).to_be_visible()
    
    # 削除ボタンをクリック
    delete_button = row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator('dialog:has(h3:has-text("グループの削除"))')
    expect(delete_modal).to_be_visible()
    
    # 削除ボタンをクリック
    delete_modal.locator('button:has-text("削除")').click()
    
    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=2000)
    
    # 削除したグループが表から消えていることを確認
    expect(page.locator('#group-table-body')).not_to_contain_text(new_name)
    # -----------------------

def test_delete_group(page: Page) -> None:
    """既存のグループを削除するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    timestamp = int(time.time())
    name_to_delete = f"削除用グループ_{timestamp}"

    page.goto("http://localhost:8000/group")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("グループ追加")').click()
    add_modal = page.locator("#add-group")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-group-name').fill(name_to_delete)
    add_modal.locator('button[form="add-group-form"]').click()
    expect(add_modal).to_be_hidden()

    # テーブルに追加されたグループが表示されていることを確認
    expect(page.locator('#group-table-body')).to_contain_text(name_to_delete)

    # 削除ボタンをクリック
    delete_button = page.locator('tr').filter(has_text=name_to_delete).locator('button:has-text("削除")')
    delete_button.click()

    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator('dialog:has(h3:has-text("グループの削除"))')
    expect(delete_modal).to_be_visible()

    # 削除ボタンをクリック
    delete_modal.locator('button:has-text("削除")').click()

    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=2000)

    # 削除したグループが表から消えていることを確認
    expect(page.locator('#group-table-body')).not_to_contain_text(name_to_delete) 