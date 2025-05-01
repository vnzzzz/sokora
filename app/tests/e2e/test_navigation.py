from playwright.sync_api import Page, expect

def test_navigate_to_locations(page: Page) -> None:
    """トップページから勤務場所管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.locator('a[title="勤務場所管理"]').click()
    expect(page).to_have_url("http://localhost:8000/locations")
    expect(page.locator("h2")).to_have_text("勤務場所管理")


def test_navigate_to_attendance(page: Page) -> None:
    """トップページから勤怠登録ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.locator('a[title="勤怠登録"]').click()
    expect(page).to_have_url("http://localhost:8000/attendance")
    expect(page.locator("h2")).to_have_text("勤怠登録")


def test_navigate_to_users(page: Page) -> None:
    """トップページから社員管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.locator('a[title="社員管理"]').click()
    expect(page).to_have_url("http://localhost:8000/user") # 実際のURLに修正
    expect(page.locator("h2")).to_have_text("社員管理")


def test_navigate_to_groups(page: Page) -> None:
    """トップページからグループ管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.locator('a[title="グループ管理"]').click()
    expect(page).to_have_url("http://localhost:8000/groups")
    expect(page.locator("h2")).to_have_text("グループ管理")


def test_navigate_to_user_types(page: Page) -> None:
    """トップページから社員種別管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.locator('a[title="社員種別管理"]').click()
    expect(page).to_have_url("http://localhost:8000/user_types")
    expect(page.locator("h2")).to_have_text("社員種別管理")


def test_navigate_to_csv(page: Page) -> None:
    """トップページからCSV出力ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.locator('a[title="CSV"]').click()
    expect(page).to_have_url("http://localhost:8000/csv")
    expect(page.locator("h2")).to_have_text("CSVデータダウンロード") 