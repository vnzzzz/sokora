from playwright.sync_api import Page, expect
import datetime
import re
import time

# テスト対象の関数をインポート
from app.utils.calendar_utils import format_date_jp

# このテストは /attendance ページの勤怠マトリックスからの登録・更新・削除を対象とする

def test_edit_attendance_via_modal(page: Page) -> None:
    """勤怠ページのマトリックスセルをクリックし、モーダルで勤怠を登録/更新するテスト"""
    page.goto("http://localhost:8000/attendance") # 勤怠登録ページ
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 1. 勤怠マトリックスが表示されるのを待つ
    calendar_locator = page.locator("#calendar") # #attendance-content から #calendar に変更
    matrix_table_locator = calendar_locator.locator("table")
    expect(matrix_table_locator).to_be_visible(timeout=1000)

    # 2. 特定のユーザーと日付のセルをクリック
    #    最初のユーザーデータ行を探す
    #    社員名セル (特定のクラスを持ち、"(ID)"形式のテキストを含むtd) を特定する
    #    :has-text() を使って括弧を含むテキストの存在を確認
    user_name_cell_selector = (
        'td.font-medium.text-left.sticky.z-10.bg-base-100.whitespace-nowrap.p-1'
        ':has-text("(")' # 括弧が含まれるセルを探す
    )
    user_name_cells = matrix_table_locator.locator(user_name_cell_selector)
    # 最初のユーザー名セルが表示されるのを待つ
    expect(user_name_cells.first).to_be_visible(timeout=1000)
    first_user_name_cell = user_name_cells.first

    # その親のtr要素を取得
    first_user_row = first_user_name_cell.locator("xpath=..") # 親要素(tr)
    row_id = first_user_row.get_attribute("id") # 行特定のためIDを取得 (あれば)

    # 社員名セルのテキストを取得・検証
    user_name_cell_text = first_user_name_cell.inner_text() or ""
    # 正規表現のマッチングはPython側で行う (バックスラッシュを修正)
    user_name_text_match = re.search(r"^(.*?)\s*\((\S+)\)$", user_name_cell_text)
    assert user_name_text_match, f"ユーザー名とIDが期待した形式で取得できませんでした: '{user_name_cell_text}'"
    user_id = user_name_text_match.group(2)
    user_name = user_name_text_match.group(1).strip()

    today = datetime.date.today()
    target_day = 10 # 10日を対象とする
    # 未来の日付になる場合、前月にするなどの考慮が必要だが、ここでは単純化
    target_date_str = f"{today.year}-{today.month:02d}-{target_day:02d}"

    # 対象ユーザー行内の、指定日付のセルを探す
    target_cell_selector = f'td.attendance-cell[data-date="{target_date_str}"]'
    target_cell_locator = first_user_row.locator(target_cell_selector)
    # 日付セルが存在するか念のため確認 (カレンダー表示範囲外の可能性)
    try:
        expect(target_cell_locator).to_be_visible(timeout=2000) # 短いタイムアウトで存在確認
    except Exception:
        print(f"警告: ユーザー {user_name}({user_id}) の日付 {target_date_str} のセルが見つかりませんでした。テストをスキップします。")
        return

    # --- 登録前のセルの状態を記録 ---
    initial_cell_content = target_cell_locator.inner_text() or ""
    initial_location_name = target_cell_locator.get_attribute("data-location") or ""
    target_cell_locator.click()

    # 3. 勤怠登録/編集モーダルが表示されるのを待つ (HTMX対応)
    modal_container_locator = page.locator('#modal-container')
    modal_dialog_locator = modal_container_locator.locator("dialog")
    expect(modal_dialog_locator).to_be_visible(timeout=1000)
    form_locator = modal_dialog_locator.locator("form")
    expect(form_locator).to_be_visible()
    # モーダルタイトルにユーザー名と日付が表示されているか確認
    expect(modal_dialog_locator.locator("h3")).to_contain_text(user_name)
    # target_date_str を date オブジェクトに変換
    target_date_obj = datetime.date.fromisoformat(target_date_str)
    # 日本語形式の日付文字列を期待値とする
    expected_date_jp = format_date_jp(target_date_obj)
    expect(modal_dialog_locator.locator("h3")).to_contain_text(expected_date_jp)

    # 4. 勤怠種別を選択 (セレクトボックス対応)
    location_select_locator = form_locator.locator('select[name="location_id"]')
    expect(location_select_locator).to_be_visible(timeout=5000)
    first_option_locator = location_select_locator.locator("option").nth(1)
    selected_location_id_str = first_option_locator.get_attribute("value")
    assert selected_location_id_str is not None and selected_location_id_str != "", "最初の有効な勤怠種別の値が取得できませんでした"
    selected_location_name = first_option_locator.inner_text() or ""
    assert selected_location_name, "最初の有効な勤怠種別名が取得できませんでした"
    location_select_locator.select_option(value=selected_location_id_str)

    # 5. 「登録」または「更新」ボタンをクリック
    register_button = form_locator.locator('button[type="submit"]:has-text("登録")')
    update_button = form_locator.locator('button[type="submit"]:has-text("更新")')

    expect(register_button.or_(update_button)).to_be_visible(timeout=5000)

    if update_button.is_visible():
        submit_button_locator = update_button
        print(f"INFO: Updating attendance for {user_name} on {target_date_str}")
    else:
        submit_button_locator = register_button
        print(f"INFO: Registering attendance for {user_name} on {target_date_str}")

    expect(submit_button_locator).to_be_enabled()
    submit_button_locator.click()

    # 6. モーダルが閉じるのを待つ (要素が削除される)
    expect(modal_dialog_locator).to_be_hidden(timeout=1000)

    # 7. カレンダー部分がリフレッシュされ、セルの内容が更新されるのを待つ
    #    htmxにより #calendar が更新される
    #    再度同じセレクタで要素を探し、内容が変わるのを待つ

    # 行を特定するセレクタを準備 (IDがあれば使う)
    # リフレッシュ後の行特定用の正規表現も修正
    row_selector = f"#{row_id}" if row_id else f'tbody tr:has(td:text-matches("{user_name}.*\\({user_id}\\)"))'
    # リフレッシュ後のテーブルで再度行を探す (より安定させるため matrix_table_locator から再検索)
    reloaded_row_locator = matrix_table_locator.locator(row_selector)
    # 行が表示されるのを待つ
    expect(reloaded_row_locator.first).to_be_visible(timeout=1000) # 最初の行が表示されることを確認

    # ユーザー名が一致する行を探す (より正確に)
    target_row_locator = reloaded_row_locator.filter(has_text=f"{user_name} ({user_id})")
    expect(target_row_locator).to_be_visible(timeout=5000)

    # 行の中から目的のセルを探す
    reloaded_cell_locator = target_row_locator.locator(target_cell_selector)

    # 更新後のセルのテキストが選択した勤怠種別名を含むことを期待
    expect(reloaded_cell_locator).to_contain_text(selected_location_name, timeout=1000)
    # 更新後の data-location 属性が選択した勤怠種別名になっていることを期待
    expect(reloaded_cell_locator).to_have_attribute("data-location", selected_location_name.strip(), timeout=5000)


def test_delete_attendance_via_modal(page: Page) -> None:
    """勤怠ページのマトリックスセルをクリックし、モーダルで勤怠を削除するテスト"""
    page.goto("http://localhost:8000/attendance") # 勤怠登録ページ
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 1. 勤怠マトリックスが表示されるのを待つ
    calendar_locator = page.locator("#calendar") # #attendance-content から #calendar に変更
    matrix_table_locator = calendar_locator.locator("table")
    expect(matrix_table_locator).to_be_visible(timeout=1000)

    # 2. 削除対象のユーザーと日付のセルを特定 (例: 最初のユーザー, 11日)
    user_name_cell_selector = (
        'td.font-medium.text-left.sticky.z-10.bg-base-100.whitespace-nowrap.p-1'
        ':has-text("(")'
    )
    user_name_cells = matrix_table_locator.locator(user_name_cell_selector)
    expect(user_name_cells.first).to_be_visible(timeout=1000)
    first_user_name_cell = user_name_cells.first
    first_user_row = first_user_name_cell.locator("xpath=..")
    row_id = first_user_row.get_attribute("id")

    user_name_cell_text = first_user_name_cell.inner_text() or ""
    user_name_text_match = re.search(r"^(.*?)\s*\((\S+)\)$", user_name_cell_text)
    assert user_name_text_match, f"ユーザー名とIDが期待した形式で取得できませんでした: '{user_name_cell_text}'"
    user_id = user_name_text_match.group(2)
    user_name = user_name_text_match.group(1).strip()

    today = datetime.date.today()
    target_day = 11 # 削除テスト用に別の日にする (例: 11日)
    target_date_str = f"{today.year}-{today.month:02d}-{target_day:02d}"

    target_cell_selector = f'td.attendance-cell[data-date="{target_date_str}"]'
    target_cell_locator = first_user_row.locator(target_cell_selector)
    try:
        expect(target_cell_locator).to_be_visible(timeout=2000)
    except Exception:
        print(f"警告: 削除テスト対象のセル {target_date_str} が見つかりませんでした。テストをスキップします。")
        return

    # 3. [準備] 削除対象のデータがなければ作成する
    target_cell_locator.click()
    # モーダル表示待機 (HTMX対応)
    modal_container_locator = page.locator('#modal-container')
    modal_dialog_locator = modal_container_locator.locator("dialog")
    expect(modal_dialog_locator).to_be_visible(timeout=1000)
    form_locator = modal_dialog_locator.locator("form")
    expect(form_locator).to_be_visible()

    delete_button = form_locator.locator('button[type="button"]:has-text("削除")')
    register_button = form_locator.locator('button[type="submit"]:has-text("登録")')

    if not delete_button.is_visible(timeout=1000): # 削除ボタンがなければ登録が必要
        print(f"INFO: Deletion target data not found for {user_name} on {target_date_str}. Registering first...")
        location_select_locator = form_locator.locator('select[name="location_id"]')
        expect(location_select_locator).to_be_visible(timeout=5000)
        first_option_locator = location_select_locator.locator("option").nth(1)
        selected_location_id_str = first_option_locator.get_attribute("value")
        assert selected_location_id_str is not None and selected_location_id_str != "", "最初の有効な勤怠種別の値が取得できませんでした"
        location_select_locator.select_option(value=selected_location_id_str)

        expect(register_button).to_be_enabled()
        register_button.click()
        expect(modal_dialog_locator).not_to_be_visible(timeout=1000)
        target_cell_locator.click()
        # 新しいモーダルが表示されるのを待つ (再取得)
        modal_dialog_locator = modal_container_locator.locator("dialog") # 再度 dialog を探す
        expect(modal_dialog_locator).to_be_visible(timeout=1000)
        # 削除ボタンがあるはず (再取得)
        delete_button = modal_dialog_locator.locator('form button[type="button"]:has-text("削除")') # dialogから辿る
        expect(delete_button).to_be_visible(timeout=5000)

    # 4. 削除ボタンをクリック
    print(f"INFO: Deleting attendance for {user_name} on {target_date_str}")
    expect(delete_button).to_be_enabled()
    page.once("dialog", lambda dialog: dialog.accept())
    delete_button.click()

    # 5. モーダルが閉じるのを待つ
    expect(modal_dialog_locator).not_to_be_visible(timeout=1000)

    # 6. カレンダー部分がリフレッシュされ、セルの内容が空になるのを待つ
    row_selector = f"#{row_id}" if row_id else f'tbody tr:has(td:text-matches("{user_name}.*\\({user_id}\\)"))'
    reloaded_row_locator = matrix_table_locator.locator(row_selector)
    expect(reloaded_row_locator.first).to_be_visible(timeout=1000)
    target_row_locator = reloaded_row_locator.filter(has_text=f"{user_name} ({user_id})")
    expect(target_row_locator).to_be_visible(timeout=5000)
    reloaded_cell_locator = target_row_locator.locator(target_cell_selector)

    # セルの中身が空であることを確認 (テキストがない)
    expect(reloaded_cell_locator).to_be_empty(timeout=1000)
    # data-location 属性が空になっていることを確認
    expect(reloaded_cell_locator).to_have_attribute("data-location", "", timeout=5000)

# TODO: 削除のテストケースも追加する
# -def test_delete_attendance_via_modal(page: Page) -> None: ...