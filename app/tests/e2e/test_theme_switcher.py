from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"


def test_theme_switcher_applies_and_persists_theme(page: Page) -> None:
    page.goto(BASE_URL)

    toggle = page.locator("#theme-toggle")
    expect(toggle).to_be_visible()
    expect(toggle).not_to_be_checked()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("body")).to_have_attribute("data-theme", "light")

    toggle.check()

    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("body")).to_have_attribute("data-theme", "dark")
    assert page.evaluate("localStorage.getItem('theme')") == "dark"

    page.reload()

    expect(page.locator("#theme-toggle")).to_be_checked()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("body")).to_have_attribute("data-theme", "dark")

    page.locator("#theme-toggle").uncheck()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    assert page.evaluate("localStorage.getItem('theme')") == "light"
