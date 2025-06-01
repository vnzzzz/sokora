from playwright.sync_api import Page, expect
import time # アサーション前の待機用

def test_add_new_location(page: Page) -> None:
    """勤怠種別管理ページで新しい勤怠種別を追加するテスト"""
    unique_location_name = f"テスト勤務地_追加_{int(time.time())}"

    # 勤怠種別管理ページにアクセス
    page.goto("http://localhost:8000/location")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 「勤怠種別追加」ボタンをクリックしてモーダルを開く
    page.locator('button:has-text("勤怠種別追加")').click()

    # モーダルを ID で特定
    add_modal_locator = page.locator("#add-location")
    expect(add_modal_locator).to_be_visible()

    # 勤怠種別名を入力
    add_modal_locator.locator('#add-location-name').fill(unique_location_name)

    # 「登録」ボタンをクリック
    add_modal_locator.locator('button[form="add-location-form"]').click()

    # モーダルが閉じることを確認（少し待機）
    expect(add_modal_locator).to_be_hidden(timeout=500)

    # 新しく追加された勤怠種別が表に表示されているかを確認
    expect(page.locator('body')).to_contain_text(unique_location_name)

    # --- テストデータ削除 ---
    row_locator = page.locator(f'tr:has-text("{unique_location_name}")')
    expect(row_locator).to_be_visible()
    
    # 削除ボタンをクリック
    delete_button = row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator('dialog:has(h3:has-text("勤怠種別の削除"))')
    expect(delete_modal).to_be_visible()
    
    # 削除ボタンをクリック
    delete_modal.locator('button:has-text("削除")').click()
    
    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=500)
    
    # 削除した勤怠種別が表から消えていることを確認
    expect(page.locator('body')).not_to_contain_text(unique_location_name)
    # -----------------------

def test_edit_location(page: Page) -> None:
    """既存の勤怠種別を編集するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    initial_name = f"テスト勤務地_編集前_{int(time.time())}"
    new_location_name = f"編集済_{initial_name}"

    page.goto("http://localhost:8000/location")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("勤怠種別追加")').click()
    add_modal = page.locator("#add-location") # ID で特定
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-location-name').fill(initial_name)
    add_modal.locator('button[form="add-location-form"]').click()
    expect(add_modal).to_be_hidden()

    # テーブルに追加された勤怠種別が表示されていることを確認
    expect(page.locator('body')).to_contain_text(initial_name)

    # 編集ボタンをクリックしてモーダルを開く
    edit_button = page.locator('tr').filter(has_text=initial_name).locator('button:has-text("編集")')
    edit_button.click()

    # 編集モーダルが表示されるのを待機
    edit_modal = page.locator('dialog:has(h3:has-text("勤怠種別編集"))')
    expect(edit_modal).to_be_visible()

    # 勤怠種別名を変更
    edit_modal.locator('input[name="name"]').fill(new_location_name)

    # 「更新」ボタンをクリック
    edit_modal.locator('.modal-action button.btn-neutral').click()

    # モーダルが閉じることを確認
    expect(edit_modal).to_be_hidden(timeout=500)

    # HTMX更新完了まで少し待機
    page.wait_for_timeout(1000)

    # 更新後の勤怠種別名が表に表示されているかを確認
    updated_row = page.locator(f'tr:has-text("{new_location_name}")')
    expect(updated_row).to_be_visible()
    
    # 古い名前だけを含む行が存在しないことを確認（編集済み_を含まない古い名前）
    old_only_row = page.locator(f'tr:has-text("{initial_name}"):not(:has-text("{new_location_name}"))')
    expect(old_only_row).not_to_be_visible()

    # --- テストデータ削除 ---
    row_locator = page.locator(f'tr:has-text("{new_location_name}")')
    expect(row_locator).to_be_visible()
    
    # 削除ボタンをクリック
    delete_button = row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator('dialog:has(h3:has-text("勤怠種別の削除"))')
    expect(delete_modal).to_be_visible()
    
    # 削除ボタンをクリック
    delete_modal.locator('button:has-text("削除")').click()
    
    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=500)
    
    # 削除した勤怠種別が表から消えていることを確認
    expect(page.locator('body')).not_to_contain_text(new_location_name)
    # -----------------------

def test_delete_location(page: Page) -> None:
    """既存の勤怠種別を削除するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    location_name_to_delete = f"テスト勤務地_削除用_{int(time.time())}"

    page.goto("http://localhost:8000/location")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("勤怠種別追加")').click()
    add_modal = page.locator("#add-location") # ID で特定
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-location-name').fill(location_name_to_delete)
    add_modal.locator('button[form="add-location-form"]').click()
    expect(add_modal).to_be_hidden()

    # テーブルに追加された勤怠種別が表示されていることを確認
    expect(page.locator('body')).to_contain_text(location_name_to_delete)

    # 削除ボタンをクリック
    delete_button = page.locator('tr').filter(has_text=location_name_to_delete).locator('button:has-text("削除")')
    delete_button.click()

    # 削除確認モーダルが表示されるのを待機
    delete_modal = page.locator('dialog:has(h3:has-text("勤怠種別の削除"))')
    expect(delete_modal).to_be_visible()

    # 削除ボタンをクリック
    delete_modal.locator('button:has-text("削除")').click()

    # モーダルが閉じることを確認
    expect(delete_modal).to_be_hidden(timeout=500)

    # 削除した勤怠種別が表から消えていることを確認
    expect(page.locator('body')).not_to_contain_text(location_name_to_delete) 