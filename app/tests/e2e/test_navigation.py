from playwright.sync_api import Page, expect

def test_navigate_to_locations(page: Page) -> None:
    """トップページから勤怠種別管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="勤怠種別管理"]').click()
    expect(page).to_have_url("http://localhost:8000/location")
    expect(page.locator("h2")).to_have_text("勤怠種別管理")


def test_navigate_to_attendance(page: Page) -> None:
    """トップページから勤怠登録ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="勤怠登録（一括）"]').click()
    expect(page).to_have_url("http://localhost:8000/attendance")
    expect(page.locator("h2")).to_have_text("勤怠登録（一括）")


def test_navigate_to_users(page: Page) -> None:
    """トップページから社員管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="社員管理"]').click()
    expect(page).to_have_url("http://localhost:8000/user")
    expect(page.locator("h2")).to_have_text("社員管理")


def test_navigate_to_groups(page: Page) -> None:
    """トップページからグループ管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="グループ管理"]').click()
    expect(page).to_have_url("http://localhost:8000/group")
    expect(page.locator("h2")).to_have_text("グループ管理")


def test_navigate_to_user_types(page: Page) -> None:
    """トップページから社員種別管理ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="社員種別管理"]').click()
    expect(page).to_have_url("http://localhost:8000/user_type")
    expect(page.locator("h2")).to_have_text("社員種別管理")


def test_navigate_to_csv(page: Page) -> None:
    """トップページからCSV出力ページへ遷移するテスト"""
    page.goto("http://localhost:8000/")
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    page.locator('a[title="CSV"]').click()
    expect(page).to_have_url("http://localhost:8000/csv")
    expect(page.locator("h2")).to_have_text("CSVデータダウンロード") 