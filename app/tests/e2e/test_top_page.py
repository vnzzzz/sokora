import re
from playwright.sync_api import Page, expect

def test_top_page_title(page: Page) -> None:
    """トップページにアクセスし、タイトルを確認するテスト"""
    page.goto("http://localhost:8000/") # アプリケーションのURLにアクセス

    # タイトルに "Sokora" が含まれていることを確認
    expect(page).to_have_title(re.compile("Sokora")) 