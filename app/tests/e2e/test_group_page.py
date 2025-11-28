# app/tests/e2e/test_group_page.py

from playwright.sync_api import Page, expect
import time
import re

BASE_URL = "http://localhost:8000"
UI_BASE = f"{BASE_URL}/ui"
GROUPS_URL = f"{UI_BASE}/groups"

def test_group_page_display(page: Page) -> None:
    """グループページが正常に表示されることをテスト"""
    page.goto(GROUPS_URL)
    expect(page.locator("body")).to_be_visible()
    expect(page.locator("h2")).to_contain_text("グループ")

def test_create_group(page: Page) -> None:
    """新しいグループを作成するテスト"""
    timestamp = int(time.time())
    group_name = f"テストグループ_{timestamp}"

    page.goto(GROUPS_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('button:has-text("グループ追加")').click()
    add_modal = page.locator("#add-group")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-group-name').fill(group_name)
    add_modal.locator('#add-group-order').fill("1")
    add_modal.locator('button[form="add-group-form"]').click()
    
    # 追加完了を待機
    page.wait_for_timeout(1000)
    
    # モーダルが閉じることを確認
    expect(add_modal).to_be_hidden(timeout=3000)
    
    # テーブル内に新しいグループが表示されることを確認
    expect(page.locator("table")).to_contain_text(group_name)

def test_edit_group(page: Page) -> None:
    """グループ編集テスト（テスト専用データを作成・編集・削除）"""
    timestamp = int(time.time())
    initial_name = f"テスト編集前グループ_{timestamp}"
    new_name = f"テスト編集済みグループ_{timestamp}"
    created_group_id = None

    page.goto(GROUPS_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    try:
        # 1. テスト用グループを作成
        page.locator('button:has-text("グループ追加")').click()
        add_modal = page.locator("#add-group")
        expect(add_modal).to_be_visible()
        add_modal.locator('#add-group-name').fill(initial_name)
        add_modal.locator('#add-group-order').fill("999")  # 末尾に配置
        add_modal.locator('button[form="add-group-form"]').click()
        
        # 追加完了を待機
        page.wait_for_timeout(1000)
        expect(add_modal).to_be_hidden(timeout=3000)
        
        # 作成されたグループがテーブルに表示されることを確認
        expect(page.locator("table")).to_contain_text(initial_name)
        
        # 2. 作成したグループの編集ボタンを特定してクリック
        # 作成したグループの行を特定
        group_row = page.locator(f'tr:has-text("{initial_name}")')
        expect(group_row).to_be_visible()
        
        # その行の編集ボタンをクリック
        edit_button = group_row.locator('button:has-text("編集")')
        edit_button.click()
        
        # 編集モーダルが表示されることを確認
        edit_modal = page.locator('.modal[open]')
        expect(edit_modal).to_be_visible()
        
        # 3. グループ名を編集
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
        # 5. テストで作成したグループを削除
        try:
            # 編集後の名前で行を特定
            test_group_row = page.locator(f'tr:has-text("{new_name}")')
            if test_group_row.is_visible():
                # 削除ボタンをクリック
                delete_button = test_group_row.locator('button:has-text("削除")')
                delete_button.click()
                
                # 削除確認モーダルが表示される場合の処理
                delete_modal = page.locator('.modal[open]')
                if delete_modal.is_visible():
                    confirm_button = delete_modal.locator('button:has-text("削除")')
                    if confirm_button.is_visible():
                        confirm_button.click()
                        page.wait_for_timeout(1000)
                
                # グループが削除されたことを確認
                page.wait_for_timeout(500)
                expect(page.locator("table")).not_to_contain_text(new_name)
        except Exception as e:
            print(f"Test cleanup failed: {e}")
    
    # 基本的な表示確認
    expect(page.locator("body")).to_be_visible()

def test_delete_group(page: Page) -> None:
    """グループ削除テスト（テスト専用データを作成・削除）"""
    timestamp = int(time.time())
    group_name = f"テスト削除用グループ_{timestamp}"

    page.goto(GROUPS_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 1. テスト用グループを作成
    page.locator('button:has-text("グループ追加")').click()
    add_modal = page.locator("#add-group")
    expect(add_modal).to_be_visible()
    add_modal.locator('#add-group-name').fill(group_name)
    add_modal.locator('#add-group-order').fill("999")
    add_modal.locator('button[form="add-group-form"]').click()
    
    # 追加完了を待機
    page.wait_for_timeout(1000)
    expect(add_modal).to_be_hidden(timeout=3000)
    
    # 作成されたグループがテーブルに表示されることを確認
    expect(page.locator("table")).to_contain_text(group_name)
    
    # 2. 作成したグループの削除ボタンをクリック
    group_row = page.locator(f'tr:has-text("{group_name}")')
    expect(group_row).to_be_visible()
    
    delete_button = group_row.locator('button:has-text("削除")')
    delete_button.click()
    
    # 削除確認モーダルが表示される場合の処理
    delete_modal = page.locator('.modal[open]')
    if delete_modal.is_visible():
        confirm_button = delete_modal.locator('button:has-text("削除")')
        if confirm_button.is_visible():
            confirm_button.click()
            page.wait_for_timeout(1000)
    
    # 3. グループが削除されたことを確認
    page.wait_for_timeout(500)
    expect(page.locator("table")).not_to_contain_text(group_name)
    
    # 基本的な表示確認
    expect(page.locator("body")).to_be_visible() 
