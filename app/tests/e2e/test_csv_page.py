"""
E2E Tests for CSV Page
"""
import re
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"

def test_csv_page_loads(page: Page) -> None:
    """CSVページが正しく読み込まれるかテストします。"""
    page.goto(f"{BASE_URL}/csv")
    
    # ページタイトルを確認
    expect(page).to_have_title(re.compile("CSV"))

    # 主要な要素が存在することを確認
    expect(page.locator('h2:has-text("CSVデータダウンロード")')).to_be_visible()
    expect(page.locator('select[name="month-select"]')).to_be_visible()
    # ダウンロードボタンのセレクタは実際のHTMLに合わせて調整が必要な場合があります
    # ここでは一般的なテキストを持つボタンまたはリンクを探します
    download_button = page.locator('button:has-text("CSVをダウンロード")').first
    expect(download_button).to_be_visible()

# TODO: 必要に応じてCSVアップロード機能のテストを追加
# 現状のルーターではアップロード機能が見当たらないため、ダウンロードのみテスト

# TODO: 可能であれば実際のダウンロード処理を（部分的に）テストする
# 例: ボタンクリックでダウンロードイベントが発生するかどうか
# def test_csv_download_click(page: Page) -> None:
#     page.goto(f"{BASE_URL}/csv")
#     download_button = page.locator('button:has-text("ダウンロード"), a:has-text("ダウンロード")').first
#
#     # Start waiting for the download
#     with page.expect_download() as download_info:
#         # Perform the action that initiates download
#         download_button.click()
#     download = download_info.value
#     # ここでダウンロードされたファイル名などを検証可能
#     print(f"Downloaded file: {download.suggested_filename}")
#     # 注意: 実際のファイル内容の検証は複雑になる場合があります 