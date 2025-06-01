from playwright.sync_api import Page, expect
import time
import re

def test_user_type_page_display(page: Page) -> None:
    """社員種別ページが正常に表示されることをテスト"""
    page.goto("http://localhost:8000/user_type")
    expect(page.locator("body")).to_be_visible()
    expect(page.locator("h2")).to_contain_text("社員種別")

def test_create_user_type(page: Page) -> None:
    """新しい社員種別を作成するテスト"""
    timestamp = int(time.time())
    user_type_name = f"テスト社員種別_{timestamp}"

    page.goto("http://localhost:8000/user_type")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("社員種別追加")').click()
    add_modal = page.locator("#add-user-type")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-user-type-name').fill(user_type_name)
    add_modal.locator('#add-user-type-order').fill("1")
    add_modal.locator('button[form="add-user-type-form"]').click()
    
    # 追加完了を待機
    page.wait_for_timeout(1000)
    
    # モーダルが閉じることを確認
    expect(add_modal).to_be_hidden(timeout=3000)
    
    # テーブル内に新しい社員種別が表示されることを確認
    expect(page.locator("table")).to_contain_text(user_type_name)

def test_edit_user_type(page: Page) -> None:
    """社員種別編集テスト（テスト専用データを作成・編集・削除）"""
    timestamp = int(time.time())
    initial_name = f"テスト編集前種別_{timestamp}"
    new_name = f"テスト編集済み種別_{timestamp}"

    page.goto("http://localhost:8000/user_type")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    try:
        # 1. テスト用社員種別を作成
        page.locator('button:has-text("社員種別追加")').click()
        add_modal = page.locator("#add-user-type")
        expect(add_modal).to_be_visible()
        add_modal.locator('#add-user-type-name').fill(initial_name)
        add_modal.locator('#add-user-type-order').fill("999")  # 末尾に配置
        add_modal.locator('button[form="add-user-type-form"]').click()
        
        # 追加完了を待機
        page.wait_for_timeout(1000)
        expect(add_modal).to_be_hidden(timeout=3000)
        
        # 作成された社員種別がテーブルに表示されることを確認
        expect(page.locator("table")).to_contain_text(initial_name)
        
        # 2. 作成した社員種別の編集ボタンを特定してクリック
        user_type_row = page.locator(f'tr:has-text("{initial_name}")')
        expect(user_type_row).to_be_visible()
        
        # その行の編集ボタンをクリック
        edit_button = user_type_row.locator('button:has-text("編集")')
        edit_button.click()
        
        # 編集モーダルが表示されることを確認
        edit_modal = page.locator('.modal[open]')
        expect(edit_modal).to_be_visible()
        
        # 3. 社員種別名を編集
        name_input = edit_modal.locator('input[name="name"]')
        expect(name_input).to_be_visible()
        name_input.fill(new_name)
        
        # 更新ボタンをクリック
        update_button = edit_modal.locator('button:has-text("更新")')
        update_button.click()
        page.wait_for_timeout(1000)
        
        # モーダルが閉じることを確認
        expect(edit_modal).to_be_hidden(timeout=3000)
        
        # 4. 編集後の名前がテーブルに表示されることを確認
        expect(page.locator("table")).to_contain_text(new_name)
        expect(page.locator("table")).not_to_contain_text(initial_name)
        
    finally:
        # 5. テストで作成した社員種別を削除
        try:
            # 編集後の名前で行を特定
            test_user_type_row = page.locator(f'tr:has-text("{new_name}")')
            if test_user_type_row.is_visible():
                # 削除ボタンをクリック
                delete_button = test_user_type_row.locator('button:has-text("削除")')
                delete_button.click()
                
                # 削除確認モーダルが表示される場合の処理
                delete_modal = page.locator('.modal[open]')
                if delete_modal.is_visible():
                    confirm_button = delete_modal.locator('button:has-text("削除")')
                    if confirm_button.is_visible():
                        confirm_button.click()
                        page.wait_for_timeout(1000)
                
                # 社員種別が削除されたことを確認
                page.wait_for_timeout(500)
                expect(page.locator("table")).not_to_contain_text(new_name)
        except Exception as e:
            print(f"Test cleanup failed: {e}")
    
    # 基本的な表示確認
    expect(page.locator("body")).to_be_visible()

def test_delete_user_type(page: Page) -> None:
    """社員種別削除テスト（テスト専用データを作成・削除）"""
    timestamp = int(time.time())
    user_type_name = f"テスト削除用種別_{timestamp}"

    page.goto("http://localhost:8000/user_type")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 1. テスト用社員種別を作成
    page.locator('button:has-text("社員種別追加")').click()
    add_modal = page.locator("#add-user-type")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-user-type-name').fill(user_type_name)
    add_modal.locator('#add-user-type-order').fill("999")
    add_modal.locator('button[form="add-user-type-form"]').click()
    
    # 追加完了を待機
    page.wait_for_timeout(1000)
    expect(add_modal).to_be_hidden(timeout=3000)
    
    # 作成された社員種別がテーブルに表示されることを確認
    expect(page.locator("table")).to_contain_text(user_type_name)
    
    # 2. 作成した社員種別の削除ボタンをクリック
    user_type_row = page.locator(f'tr:has-text("{user_type_name}")')
    expect(user_type_row).to_be_visible()
    
    delete_button = user_type_row.locator('button:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示される場合の処理
    delete_modal = page.locator('.modal[open]')
    if delete_modal.is_visible():
        confirm_button = delete_modal.locator('button:has-text("削除")')
        if confirm_button.is_visible():
            confirm_button.click()
            page.wait_for_timeout(1000)
    
    # 3. 社員種別が削除されたことを確認
    page.wait_for_timeout(500)
    expect(page.locator("table")).not_to_contain_text(user_type_name)
    
    # 基本的な表示確認
    expect(page.locator("body")).to_be_visible() 