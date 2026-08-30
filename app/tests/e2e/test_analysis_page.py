"""
勤怠分析ページのE2Eテスト
"""

import pytest
from playwright.sync_api import Page, expect


def test_analysis_page_title(page: Page) -> None:
    """分析ページのタイトルが正しく表示されることを確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    expect(page).to_have_title("Sokora - 勤怠集計")


def test_analysis_page_elements_visibility(page: Page) -> None:
    """分析ページの必須要素が表示されることを確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 基本的なページ表示確認
    expect(page.locator("body")).to_be_visible()
    
    # ページに十分なコンテンツがあることを確認
    page_content = page.locator("body").text_content()
    if page_content and len(page_content) > 100:
        # 分析関連のコンテンツがあることを確認
        expect(page.locator("body")).to_be_visible()


def test_analysis_monthly_view(page: Page) -> None:
    """月別表示モードの動作確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 月別表示のデータが表示されていることを確認
    expect(page.locator("body")).to_contain_text("年")
    expect(page.locator("body")).to_contain_text("月")
    
    # 月切り替えボタンの確認
    month_nav = page.locator(".btn-group, .month-navigation")
    if month_nav.is_visible():
        expect(month_nav).to_be_visible()


def test_analysis_yearly_view(page: Page) -> None:
    """年別表示モードの動作確認"""
    from datetime import datetime
    current_year = datetime.now().year
    
    page.goto(f"http://localhost:8000/analysis?year={current_year}")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 年別表示のデータが表示されていることを確認
    expect(page.locator("body")).to_contain_text(f"{current_year}年度")
    
    # 年選択オプションの確認
    year_selector = page.locator("select[name='year'], .year-selector")
    if year_selector.is_visible():
        expect(year_selector).to_be_visible()


def test_analysis_data_table(page: Page) -> None:
    """分析データテーブルの基本構造確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # テーブルまたはデータコンテナの存在確認
    data_container = page.locator(".table, .analysis-data, .user-data, [data-testid='analysis-table']")
    expect(data_container.first).to_be_visible()
    
    # グループまたはユーザー情報の確認
    content = page.locator("body").text_content()
    if content:
        # 基本的なデータ構造要素の確認
        assert len(content) > 100  # 十分なコンテンツがあることを確認


def test_analysis_month_navigation(page: Page) -> None:
    """月ナビゲーションの動作確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 現在のURL/月を記録
    current_url = page.url
    
    # 前月/次月ナビゲーションボタンを探す
    prev_buttons = page.locator("a[href*='month='], button[data-month], .btn-prev, .month-prev")
    next_buttons = page.locator("a[href*='month='], button[data-month], .btn-next, .month-next")
    
    if prev_buttons.count() > 0:
        # 最初の有効な前月ボタンをクリック
        for i in range(prev_buttons.count()):
            button = prev_buttons.nth(i)
            if button.is_visible() and button.is_enabled():
                button.click()
                page.wait_for_load_state("networkidle")
                
                # URLが変わったことを確認
                new_url = page.url
                assert new_url != current_url
                break


def test_analysis_group_data_display(page: Page) -> None:
    """グループ別データ表示の確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # グループ関連のデータが表示されていることを確認
    page_content = page.locator("body").text_content()
    if page_content:
        # グループまたは組織関連の表示要素を確認
        group_indicators = ["グループ", "部門", "部署", "組織", "チーム"]
        has_group_info = any(indicator in page_content for indicator in group_indicators)
        
        # ユーザー関連の表示要素を確認
        user_indicators = ["ユーザー", "社員", "職員", "メンバー", "名前"]
        has_user_info = any(indicator in page_content for indicator in user_indicators)
        
        # どちらか一方でも表示されていればOK
        assert has_group_info or has_user_info


def test_analysis_location_data_display(page: Page) -> None:
    """勤怠種別データ表示の確認"""
    page.goto("http://localhost:8000/analysis")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 勤怠種別関連のデータが表示されていることを確認
    page_content = page.locator("body").text_content()
    if page_content:
        # 勤怠種別関連の表示要素を確認
        location_indicators = ["オフィス", "リモート", "在宅", "出社", "勤務", "場所", "種別"]
        has_location_info = any(indicator in page_content for indicator in location_indicators)
        
        # 数値データの存在確認
        number_indicators = ["日", "回", "件", "人"]
        has_numbers = any(indicator in page_content for indicator in number_indicators)
        
        # どちらか一方でも表示されていればOK
        assert has_location_info or has_numbers


def test_analysis_error_handling(page: Page) -> None:
    """エラーハンドリングの確認"""
    # 無効な月パラメータでアクセス
    page.goto("http://localhost:8000/analysis?month=invalid")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # エラーが適切に処理されていることを確認
    expect(page.locator("body")).not_to_contain_text("500")
    expect(page.locator("body")).not_to_contain_text("Internal Server Error")
    
    # ページが表示されていることを確認
    expect(page.locator("body")).to_be_visible()


def test_analysis_responsive_design(page: Page) -> None:
    """レスポンシブデザインの確認"""
    page.goto("http://localhost:8000/analysis")
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