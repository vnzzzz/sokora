from datetime import date, timedelta

from playwright.sync_api import Page, expect

ANALYSIS_URL = "http://localhost:8000/analysis"


def test_analysis_month_change_updates_dom_and_history(page: Page) -> None:
    page.goto(ANALYSIS_URL)
    expect(page).to_have_title("Sokora - 勤怠集計")
    expect(page.locator("[data-testid='analysis-table']")).to_be_visible()
    expect(page.locator("#period-month")).to_be_checked()

    first_of_month = date.today().replace(day=1)
    previous_month = first_of_month - timedelta(days=1)
    target_month = previous_month.strftime("%Y-%m")
    target_label = f"{previous_month.year}年{previous_month.month}月"

    month_input = page.locator("#month-input")
    month_input.fill(target_month)
    month_input.dispatch_event("change")

    expect(page.locator(".analysis-period-label")).to_have_text(
        target_label,
        timeout=5000,
    )
    expect(page).to_have_url(
        f"{ANALYSIS_URL}?month={target_month}",
        timeout=5000,
    )
    expect(page.locator("#month-input")).to_have_value(target_month)
    expect(page.locator("[data-testid='analysis-table']")).to_be_visible()
