from datetime import date, timedelta

from playwright.sync_api import Page, expect

ANALYSIS_URL = "http://localhost:8000/analysis"


def test_analysis_month_change_updates_dom_and_history(page: Page) -> None:
    page.goto(ANALYSIS_URL)
    expect(page).to_have_title("Sokora - 勤怠集計")
    initial_label = page.locator(".analysis-period-label").inner_text()
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

    page.go_back()
    expect(page).to_have_url(ANALYSIS_URL, timeout=5000)
    expect(page.locator(".analysis-period-label")).to_have_text(
        initial_label, timeout=5000
    )


def test_analysis_period_mode_switch_uses_htmx_navigation(page: Page) -> None:
    page.goto(ANALYSIS_URL)

    page.locator("#period-year").check()

    expect(page.locator("#period-year")).to_be_checked(timeout=5000)
    expect(page.locator("#year-selection")).to_be_visible()
    expect(page.locator(".analysis-period-label")).to_contain_text("年度")
    selected_year = page.locator("#year-select").input_value()
    expect(page).to_have_url(
        f"{ANALYSIS_URL}?mode=year&year={selected_year}",
        timeout=5000,
    )

    current_month = date.today().strftime("%Y-%m")
    page.locator("#period-month").check()

    expect(page.locator("#period-month")).to_be_checked(timeout=5000)
    expect(page.locator("#month-selection")).to_be_visible()
    expect(page).to_have_url(f"{ANALYSIS_URL}?month={current_month}", timeout=5000)


def test_analysis_location_filter_updates_table_without_changing_url(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    checkbox = page.locator(".location-checkbox").first
    location_id = checkbox.get_attribute("value")
    assert location_id is not None

    header = page.locator(f".location-header[data-location-id='{location_id}']")
    expect(header).to_be_hidden()
    initial_url = page.url

    checkbox.check()

    expect(page.locator(f"#location-{location_id}")).to_be_checked(timeout=5000)
    expect(header).to_be_visible(timeout=5000)
    expect(page).to_have_url(initial_url)
