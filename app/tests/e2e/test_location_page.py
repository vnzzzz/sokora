from playwright.sync_api import Page, expect
import time # アサーション前の待機用

BASE_URL = "http://localhost:8000"
UI_BASE = f"{BASE_URL}/ui"
LOCATIONS_URL = f"{UI_BASE}/locations"

def test_location_page_display(page: Page) -> None:
    """勤怠種別ページが正常に表示されることをテスト"""
    page.goto(LOCATIONS_URL)
    expect(page.locator("body")).to_be_visible()
    expect(page.locator("h2")).to_contain_text("勤怠種別")

def test_create_location(page: Page) -> None:
    """新しい勤怠種別を作成するテスト"""
    timestamp = int(time.time())
    location_name = f"テスト勤務地_{timestamp}"

    page.goto(LOCATIONS_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("勤怠種別追加")').click()
    add_modal = page.locator("#add-location")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-location-name').fill(location_name)
    add_modal.locator('#add-location-category').fill("テスト")
    add_modal.locator('#add-location-order').fill("1")
    add_modal.locator('button[form="add-location-form"]').click()
    
    # 追加完了を待機
    page.wait_for_timeout(1000)
    
    # モーダルが閉じることを確認
    expect(add_modal).to_be_hidden(timeout=3000)
    
    # メインコンテンツエリア内のテーブルで新しい勤怠種別が表示されることを確認
    main_table = page.locator("main").locator("table").last
    expect(main_table).to_contain_text(location_name)

def test_edit_location(page: Page) -> None:
    """勤怠種別編集テスト（テスト専用データを作成・編集・削除）"""
    timestamp = int(time.time())
    initial_name = f"テスト編集前勤務地_{timestamp}"
    new_location_name = f"テスト編集済み勤務地_{timestamp}"

    page.goto(LOCATIONS_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    try:
        # 1. テスト用勤怠種別を作成
        page.locator('button:has-text("勤怠種別追加")').click()
        add_modal = page.locator("#add-location")
        expect(add_modal).to_be_visible()
        add_modal.locator('#add-location-name').fill(initial_name)
        add_modal.locator('#add-location-category').fill("テスト")
        add_modal.locator('#add-location-order').fill("999")  # 末尾に配置
        add_modal.locator('button[form="add-location-form"]').click()
        
        # 追加完了を待機
        page.wait_for_timeout(1000)
        expect(add_modal).to_be_hidden(timeout=3000)
        
        # 作成された勤怠種別がメインテーブルに表示されることを確認
        main_table = page.locator("main").locator("table").last
        expect(main_table).to_contain_text(initial_name)
        
        # 2. 作成した勤怠種別の編集ボタンを特定してクリック
        location_row = page.locator(f'tr:has-text("{initial_name}")')
        expect(location_row).to_be_visible()
        
        # その行の編集ボタンをクリック
        edit_button = location_row.locator('button:has-text("編集")')
        edit_button.click()
        
        # 編集モーダルが表示されることを確認
        edit_modal = page.locator('.modal[open]')
        expect(edit_modal).to_be_visible()
        
        # 3. 勤怠種別名を編集
        name_input = edit_modal.locator('input[name="name"]')
        expect(name_input).to_be_visible()
        name_input.fill(new_location_name)
        
        # 更新ボタンをクリック
        update_button = edit_modal.locator('button:has-text("更新")')
        update_button.click()
        page.wait_for_timeout(1000)
        
        # モーダルが閉じることを確認
        expect(edit_modal).to_be_hidden(timeout=3000)
        
        # 4. 編集後の名前がメインテーブルに表示されることを確認
        expect(main_table).to_contain_text(new_location_name)
        expect(main_table).not_to_contain_text(initial_name)
        
    finally:
        # 5. テストで作成した勤怠種別を削除
        try:
            # 編集後の名前で行を特定
            test_location_row = page.locator(f'tr:has-text("{new_location_name}")')
            if test_location_row.is_visible():
                # 削除ボタンをクリック
                delete_button = test_location_row.locator('button:has-text("削除")')
                delete_button.click()
                
                # 削除確認モーダルが表示される場合の処理
                delete_modal = page.locator('.modal[open]')
                if delete_modal.is_visible():
                    confirm_button = delete_modal.locator('button:has-text("削除")')
                    if confirm_button.is_visible():
                        confirm_button.click()
                        page.wait_for_timeout(1000)
                
                # 勤怠種別が削除されたことを確認
                page.wait_for_timeout(500)
                expect(main_table).not_to_contain_text(new_location_name)
        except Exception as e:
            print(f"Test cleanup failed: {e}")
    
    # 基本的な表示確認
    expect(page.locator("body")).to_be_visible()

def test_delete_location(page: Page) -> None:
    """勤怠種別削除テスト（テスト専用データを作成・削除）"""
    timestamp = int(time.time())
    location_name = f"テスト削除用勤務地_{timestamp}"

    page.goto(LOCATIONS_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 1. テスト用勤怠種別を作成
    page.locator('button:has-text("勤怠種別追加")').click()
    add_modal = page.locator("#add-location")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-location-name').fill(location_name)
    add_modal.locator('#add-location-category').fill("テスト")
    add_modal.locator('#add-location-order').fill("999")
    add_modal.locator('button[form="add-location-form"]').click()
    
    # 追加完了を待機
    page.wait_for_timeout(1000)
    expect(add_modal).to_be_hidden(timeout=3000)
    
    # 作成された勤怠種別がメインテーブルに表示されることを確認
    main_table = page.locator("main").locator("table").last
    expect(main_table).to_contain_text(location_name)
    
    # 2. 作成した勤怠種別の削除ボタンをクリック
    location_row = page.locator(f'tr:has-text("{location_name}")')
    expect(location_row).to_be_visible()
    
    delete_button = location_row.locator('button:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示される場合の処理
    delete_modal = page.locator('.modal[open]')
    if delete_modal.is_visible():
        confirm_button = delete_modal.locator('button:has-text("削除")')
        if confirm_button.is_visible():
            confirm_button.click()
            page.wait_for_timeout(1000)
    
    # 3. 勤怠種別が削除されたことを確認
    page.wait_for_timeout(500)
    expect(main_table).not_to_contain_text(location_name)
    
    # 基本的な表示確認
    expect(page.locator("body")).to_be_visible() 
