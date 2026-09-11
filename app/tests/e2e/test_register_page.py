import re

from playwright.sync_api import Page, expect

MONTHLY_URL = "http://localhost:8000/attendance/monthly"


def test_register_user_selection_and_month_navigation_use_htmx(page: Page) -> None:
    page.goto(MONTHLY_URL)
    expect(page).to_have_title("Sokora - 勤怠登録（個別）")

    user_link = page.locator("#user-list a[hx-get]").first
    expect(user_link).to_be_visible()
    hx_get = user_link.get_attribute("hx-get")
    assert hx_get is not None
    match = re.search(r"/attendance/monthly/users/([^?]+)", hx_get)
    assert match is not None
    user_id = match.group(1)

    user_link.click()

    calendar = page.locator("#user-calendar")
    expect(calendar).to_have_attribute("data-user-id", user_id)
    initial_month = calendar.get_attribute("data-month")
    assert initial_month is not None
    expect(calendar.locator("td.attendance-cell").first).to_be_visible()

    next_button = calendar.get_by_role("button", name="▶︎")
    expect(next_button).to_be_visible()
    next_button.click()

    expect(calendar).not_to_have_attribute("data-month", initial_month)
    next_month = calendar.get_attribute("data-month")
    assert next_month is not None and next_month != initial_month
    expect(calendar).to_have_attribute("data-user-id", user_id)

    current_button = calendar.get_by_role("button", name="今月")
    current_button.click()
    expect(calendar).not_to_have_attribute("data-month", next_month)


def test_register_calendar_keeps_equal_day_columns_on_narrow_viewport(
    page: Page,
) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(MONTHLY_URL)

    user_link = page.locator("#user-list a[hx-get]").first
    expect(user_link).to_be_visible()
    user_link.click()

    calendar = page.locator("#user-calendar")
    headers = calendar.locator("thead th")
    expect(headers).to_have_count(7)
    expect(calendar.locator("td.attendance-cell").first).to_be_visible()

    widths = headers.evaluate_all(
        "elements => elements.map(element => element.getBoundingClientRect().width)"
    )

    assert widths
    assert max(widths) - min(widths) < 1
