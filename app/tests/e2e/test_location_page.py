from playwright.sync_api import Page, expect
import time # アサーション前の待機用

def test_add_new_location(page: Page) -> None:
    """勤務場所管理ページで新しい勤務場所を追加するテスト"""
    unique_location_name = f"テスト勤務地_追加_{int(time.time())}"

    # 勤務場所管理ページにアクセス
    page.goto("http://localhost:8000/locations")

    # 「勤務場所追加」ボタンをクリックしてモーダルを開く
    page.locator('button:has-text("勤務場所追加")').click()

    # モーダルを ID で特定
    add_modal_locator = page.locator("#add-location-modal")
    expect(add_modal_locator).to_be_visible()

    # 勤務場所名を入力
    add_modal_locator.locator('#add-location-name').fill(unique_location_name)

    # 「追加」ボタンをクリックしてフォームを送信
    add_modal_locator.locator('button[type="submit"]').click()

    # テーブルが更新され、新しい勤務場所が表示されるのを待機・確認
    expect(page.locator("#location-table-body")).to_contain_text(unique_location_name)
    expect(add_modal_locator).not_to_be_visible() # モーダルが閉じることを確認

def test_edit_location(page: Page) -> None:
    """既存の勤務場所を編集するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    initial_name = f"テスト勤務地_編集前_{int(time.time())}"
    new_location_name = f"編集済_{initial_name}"

    page.goto("http://localhost:8000/locations")
    page.locator('button:has-text("勤務場所追加")').click()
    add_modal = page.locator("#add-location-modal") # ID で特定
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-location-name').fill(initial_name)
    add_modal.locator('button[type="submit"]').click()
    # 追加されたことをテーブルで確認 (待機も兼ねる)
    expect(page.locator("#location-table-body")).to_contain_text(initial_name)
    expect(add_modal).not_to_be_visible()
    # ------------------------------------

    # 編集対象の行を見つける (テキストで特定し、IDを取得)
    row_locator = page.locator(f'#location-table-body tr:has-text("{initial_name}")')
    expect(row_locator).to_be_visible()
    # 行 ID から location_id を取得 (例: 'location-row-5' -> 5)
    row_id = row_locator.get_attribute('id')
    assert row_id is not None, f"Row ID attribute not found for row with text: {initial_name}"
    location_id_str = row_id.split('-')[-1]
    assert location_id_str.isdigit(), "Failed to extract location ID from row ID"
    location_id = int(location_id_str)

    # その行の中の編集ボタンをクリック
    row_locator.locator('button:has-text("編集")').click()

    # 編集モーダルが表示されるのを待機 (IDで特定)
    edit_modal_locator = page.locator(f"#edit-form-location-{location_id}")
    expect(edit_modal_locator).to_be_visible()
    # HTMXでロードされるコンテンツ内の input を待機
    expect(edit_modal_locator.locator('input[name="name"]')).to_have_value(initial_name, timeout=5000)

    # 新しい勤務場所名を入力
    edit_modal_locator.locator('input[name="name"]').fill(new_location_name)

    # 「保存」ボタンをクリックしてフォームを送信 (テキスト修正)
    edit_modal_locator.locator('button[type="submit"]:has-text("保存")').click()

    # テーブルが更新され、新しい名前が表示されるのを待機・確認
    # 更新後も行 ID は変わらないはず
    updated_row_locator = page.locator(f"#location-row-{location_id}")
    # 行内の最初の <td> 要素のテキストをチェック
    expect(updated_row_locator.locator("td").first).to_have_text(new_location_name)
    expect(edit_modal_locator).not_to_be_visible()

def test_delete_location(page: Page) -> None:
    """既存の勤務場所を削除するテスト"""
    # --- テストデータ準備 (UI操作で追加) ---
    location_name_to_delete = f"テスト勤務地_削除用_{int(time.time())}"

    page.goto("http://localhost:8000/locations")
    page.locator('button:has-text("勤務場所追加")').click()
    add_modal = page.locator("#add-location-modal") # ID で特定
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-location-name').fill(location_name_to_delete)
    add_modal.locator('button[type="submit"]').click()
    expect(page.locator("#location-table-body")).to_contain_text(location_name_to_delete)
    expect(add_modal).not_to_be_visible()
    # ------------------------------------

    # 削除対象の行を見つける (テキストで特定し、IDを取得)
    row_locator = page.locator(f'#location-table-body tr:has-text("{location_name_to_delete}")')
    expect(row_locator).to_be_visible()
    row_id = row_locator.get_attribute('id')
    assert row_id is not None, f"Row ID attribute not found for row with text: {location_name_to_delete}"
    location_id_str = row_id.split('-')[-1]
    assert location_id_str.isdigit(), "Failed to extract location ID from row ID"
    location_id = int(location_id_str)

    # その行の中の削除ボタンをクリック (テキストとクラスでより詳細に特定)
    row_locator.locator('button.btn-sm.btn-error.btn-outline:has-text("削除")').click()

    # 削除確認モーダル内のフォームが表示されるのを待機 (ID修正)
    delete_form_locator = page.locator(f"#delete-form-{location_id}")
    expect(delete_form_locator).to_be_visible()

    # モーダル内の「削除」ボタンをクリック (hx-delete 属性で特定)
    delete_form_locator.locator('button[hx-delete]').click()

    # 行が削除されたことを確認 (見えなくなる)
    expect(row_locator).not_to_be_visible()
    # (オプション) 成功のトーストメッセージが表示されることを確認
    # expect(page.locator("#toast-container")).to_contain_text("削除しました") 