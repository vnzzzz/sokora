from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"
UI_BASE = BASE_URL


def test_navigate_to_locations(page: Page) -> None:
    """トップページから勤怠種別管理ページへ遷移するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="勤怠種別管理"]').click()
    expect(page).to_have_url(f"{UI_BASE}/locations")
    expect(page.locator("h2")).to_have_text("勤怠種別管理")


def test_navigate_to_attendance(page: Page) -> None:
    """トップページから勤怠登録ページへ遷移するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="勤怠登録（一括）"]').click()
    expect(page).to_have_url(f"{UI_BASE}/attendance/weekly")
    expect(page.locator("h2")).to_have_text("勤怠登録（一括）")


def test_navigate_to_users(page: Page) -> None:
    """トップページから社員管理ページへ遷移するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="社員管理"]').click()
    expect(page).to_have_url(f"{UI_BASE}/users")
    expect(page.locator("h2")).to_have_text("社員管理")


def test_navigate_to_groups(page: Page) -> None:
    """トップページからグループ管理ページへ遷移するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="グループ管理"]').click()
    expect(page).to_have_url(f"{UI_BASE}/groups")
    expect(page.locator("h2")).to_have_text("グループ管理")


def test_navigate_to_user_types(page: Page) -> None:
    """トップページから社員種別管理ページへ遷移するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="社員種別管理"]').click()
    expect(page).to_have_url(f"{UI_BASE}/user-types")
    expect(page.locator("h2")).to_have_text("社員種別管理")


def test_navigate_to_csv(page: Page) -> None:
    """トップページからCSV出力ページへ遷移するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="CSV"]').click()
    expect(page).to_have_url(f"{UI_BASE}/csv")
    expect(page.locator("h2")).to_have_text("CSVデータダウンロード")
