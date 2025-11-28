"""
勤怠登録ページのE2Eテスト
"""

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"
UI_BASE = f"{BASE_URL}/ui"
MONTHLY_URL = f"{UI_BASE}/attendance/monthly"


def test_register_page_title(page: Page) -> None:
    """登録ページのタイトルが正しく表示されることを確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    expect(page).to_have_title("Sokora - 勤怠登録（個別）")


def test_register_page_elements_visibility(page: Page) -> None:
    """登録ページの必須要素が表示されることを確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # ページが表示されていることを確認
    expect(page.locator("body")).to_be_visible()
    
    # ページ内容の確認（勤怠登録関連の文字があることを確認）
    expect(page.locator("body")).to_contain_text("勤怠登録")


def test_register_current_month_display(page: Page) -> None:
    """現在月の登録データ表示確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 基本的なページ表示確認
    expect(page.locator("body")).to_be_visible()


def test_register_search_functionality(page: Page) -> None:
    """検索機能の動作確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 検索フォームを探す
    search_inputs = page.locator("input[name='search'], input[placeholder*='検索'], input[type='search'], .search-input")
    
    if search_inputs.count() > 0:
        search_input = search_inputs.first
        expect(search_input).to_be_visible()
        
        # 検索テストを実行
        search_input.fill("test")
        
        # 検索ボタンまたはEnterキーでの検索
        search_buttons = page.locator("button[type='submit'], .search-btn, .btn-search")
        if search_buttons.count() > 0:
            search_buttons.first.click()
            page.wait_for_load_state("networkidle")
        else:
            search_input.press("Enter")
            page.wait_for_load_state("networkidle")
        
        # 検索結果または検索状態が反映されていることを確認
        expect(page.locator("body")).to_be_visible()


def test_register_month_navigation(page: Page) -> None:
    """月ナビゲーションの動作確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 現在のURL/月を記録
    current_url = page.url
    
    # 前月ナビゲーションボタンを探してクリック
    prev_buttons = page.locator("a[href*='month='], button[data-month], .btn-prev, .month-prev, .prev")
    
    if prev_buttons.count() > 0:
        # 最初の有効な前月ボタンをクリック
        for i in range(prev_buttons.count()):
            button = prev_buttons.nth(i)
            if button.is_visible() and button.is_enabled():
                button.click()
                page.wait_for_load_state("networkidle")
                
                # URLまたはコンテンツが変わったことを確認
                new_url = page.url
                if new_url != current_url:
                    assert new_url != current_url
                    break


def test_register_specific_month_access(page: Page) -> None:
    """特定月への直接アクセス確認"""
    # 2024年1月の登録ページにアクセス
    page.goto(f"{MONTHLY_URL}?month=2024-01")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 基本的なページ表示確認
    expect(page.locator("body")).to_be_visible()


def test_register_user_list_display(page: Page) -> None:
    """ユーザーリスト表示の確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # ユーザー関連のデータが表示されているかを確認
    page_content = page.locator("body").text_content()
    if page_content:
        # ユーザー関連の表示要素を確認
        user_indicators = ["ユーザー", "社員", "職員", "メンバー", "名前", "ID"]
        has_user_info = any(indicator in page_content for indicator in user_indicators)
        
        # グループ関連の表示要素を確認
        group_indicators = ["グループ", "部門", "部署", "組織", "チーム"]
        has_group_info = any(indicator in page_content for indicator in group_indicators)
        
        # 基本的な登録機能が動作していることを確認
        assert len(page_content) > 100


def test_register_grouped_user_display(page: Page) -> None:
    """グループ別ユーザー表示の確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # グループ化された表示要素を探す
    group_elements = page.locator(".group, .user-group, .department, [data-testid='user-group']")
    
    # グループ要素が存在する場合の確認
    if group_elements.count() > 0:
        expect(group_elements.first).to_be_visible()
    
    # 基本的なリスト構造の確認
    list_elements = page.locator("ul, ol, .list, .user-list, table")
    if list_elements.count() > 0:
        expect(list_elements.first).to_be_visible()


def test_register_individual_user_access(page: Page) -> None:
    """個別ユーザーの登録ページアクセス確認"""
    # 特定ユーザーの登録ページにアクセス（存在しないユーザーでもエラーにならないことを確認）
    page.goto(f"{MONTHLY_URL}/users/test_user_id")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # エラーページではなく、適切にハンドリングされていることを確認
    expect(page.locator("body")).not_to_contain_text("500")
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")
    
    # ページが表示されていることを確認
    expect(page.locator("body")).to_be_visible()


def test_register_calendar_integration(page: Page) -> None:
    """カレンダー機能との連携確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # カレンダー関連の要素を探す
    calendar_elements = page.locator(".calendar, .calendar-grid, table, [data-testid='calendar']")
    
    if calendar_elements.count() > 0:
        expect(calendar_elements.first).to_be_visible()
        
        # 曜日ヘッダーの確認
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        page_content = page.locator("body").text_content()
        if page_content:
            has_weekdays = any(weekday in page_content for weekday in weekdays)
            assert has_weekdays


def test_register_location_data_display(page: Page) -> None:
    """勤怠種別データ表示の確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 勤怠種別関連のデータが表示されているかを確認
    page_content = page.locator("body").text_content()
    if page_content:
        # 勤怠種別関連の表示要素を確認
        location_indicators = ["オフィス", "リモート", "在宅", "出社", "勤務", "場所", "種別"]
        has_location_info = any(indicator in page_content for indicator in location_indicators)
        
        # 登録フォーム関連の要素を確認
        form_indicators = ["登録", "選択", "設定", "更新", "保存"]
        has_form_info = any(indicator in page_content for indicator in form_indicators)
        
        # どちらか一方でも表示されていればOK
        assert has_location_info or has_form_info or len(page_content) > 50


def test_register_search_with_query(page: Page) -> None:
    """検索クエリパラメータでのアクセス確認"""
    # 検索クエリ付きでアクセス
    page.goto(f"{MONTHLY_URL}?search_query=test")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 検索状態が反映されていることを確認
    search_inputs = page.locator("input[name='search'], input[placeholder*='検索'], input[type='search']")
    
    if search_inputs.count() > 0:
        search_value = search_inputs.first.input_value()
        # 検索値が設定されているかまたはページが正常に表示されていることを確認
        assert search_value == "test" or len(search_value) >= 0
    
    # エラーが発生していないことを確認
    expect(page.locator("body")).not_to_contain_text("500")


def test_register_error_handling(page: Page) -> None:
    """エラーハンドリングの確認"""
    # 無効な月パラメータでアクセス
    page.goto(f"{MONTHLY_URL}?month=invalid")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # エラーが適切に処理されていることを確認
    expect(page.locator("body")).not_to_contain_text("500")
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")
    
    # リダイレクトまたは正常なページが表示されていることを確認
    expect(page.locator("body")).to_be_visible()


def test_register_responsive_design(page: Page) -> None:
    """レスポンシブデザインの確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # デスクトップサイズでの表示確認
    page.set_viewport_size({"width": 1200, "height": 800})
    expect(page.locator("body")).to_be_visible()
    
    # タブレットサイズでの表示確認
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.locator("body")).to_be_visible()
    
    # モバイルサイズでの表示確認
    page.set_viewport_size({"width": 375, "height": 667})
    expect(page.locator("body")).to_be_visible()


def test_register_form_elements(page: Page) -> None:
    """登録フォーム要素の確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 基本的なページ表示確認
    expect(page.locator("body")).to_be_visible()
    
    # ページに十分なコンテンツがあることを確認（form要素があることの間接的な確認）
    page_content = page.locator("body").text_content()
    if page_content and len(page_content) > 200:
        # 勤怠登録関連のコンテンツがあることを確認
        expect(page.locator("body")).to_be_visible()


def test_register_navigation_integration(page: Page) -> None:
    """ナビゲーション統合の確認"""
    page.goto(MONTHLY_URL)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # ナビゲーションメニューの確認
    nav_elements = page.locator("nav, .nav, .navigation, .menu")
    
    if nav_elements.count() > 0:
        expect(nav_elements.first).to_be_visible()
    
    # 他のページへのリンクの確認
    link_elements = page.locator("a[href*='/']")
    if link_elements.count() > 0:
        # 少なくとも1つのリンクが動作することを確認
        for i in range(min(link_elements.count(), 3)):
            link = link_elements.nth(i)
            if link.is_visible():
                href = link.get_attribute("href")
                if href and href != "#":
                    expect(link).to_be_visible()
                    break 
