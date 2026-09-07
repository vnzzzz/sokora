from playwright.sync_api import Page, expect

TOP_URL = "http://localhost:8000"


def test_top_calendar_htmx_navigation_and_day_detail(page: Page) -> None:
    page.goto(TOP_URL)
    expect(page.locator("h2")).to_have_text("勤怠確認")

    calendar = page.locator("#calendar-area")
    detail = page.locator("#detail-area")
    first_cell = calendar.locator(".calendar-cell[data-date]").first
    expect(first_cell).to_be_visible(timeout=5000)

    target_date = first_cell.get_attribute("data-date")
    assert target_date is not None
    first_cell.click()
    expect(detail).to_contain_text(
        f"{target_date}の勤怠情報",
        timeout=5000,
    )

    month_label = calendar.locator(".text-xl.font-bold")
    initial_month = month_label.text_content()
    assert initial_month is not None

    next_button = calendar.locator(".btn-group button").last
    next_button.click()
    expect(month_label).not_to_have_text(initial_month, timeout=5000)

    current_button = calendar.locator(".btn-group .btn-neutral")
    current_button.click()
    expect(month_label).to_have_text(initial_month, timeout=5000)
