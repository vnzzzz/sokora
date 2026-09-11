from datetime import date, timedelta

from playwright.sync_api import Page, expect

ANALYSIS_URL = "http://localhost:8000/analysis"


def test_analysis_month_change_updates_dom_and_history(page: Page) -> None:
    page.goto(ANALYSIS_URL)
    expect(page).to_have_title("Sokora - 勤怠集計")
    initial_label = page.locator(".analysis-period-label").inner_text()
    expect(page.locator("[data-testid='analysis-table']")).to_be_visible()
    expect(page.get_by_test_id("analysis-month-period")).to_contain_text("表示中")
    expect(page.get_by_test_id("analysis-year-period")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-chart")).to_contain_text("日別推移")

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
    expect(page.get_by_test_id("analysis-month-period")).to_contain_text("表示中")
    expect(page.locator("[data-testid='analysis-table']")).to_be_visible()

    page.go_back()
    expect(page).to_have_url(ANALYSIS_URL, timeout=5000)
    expect(page.locator(".analysis-period-label")).to_have_text(
        initial_label, timeout=5000
    )


def test_analysis_month_and_fiscal_year_periods_are_independent_htmx_inputs(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    expect(page.get_by_role("heading", name="月次集計")).to_be_visible()
    expect(page.get_by_role("heading", name="年度集計")).to_be_visible()
    expect(page.locator("#month-input")).to_be_visible()
    expect(page.locator("#year-select")).to_be_visible()
    expect(page.get_by_test_id("analysis-month-period")).to_contain_text("表示中")

    selected_year = page.locator("#year-select").input_value()
    page.locator("#year-select").dispatch_event("change")

    expect(page.get_by_test_id("analysis-year-period")).to_contain_text(
        "表示中", timeout=5000
    )
    expect(page.locator(".analysis-period-label")).to_contain_text("年度")
    expect(page.get_by_test_id("analysis-trend-chart")).to_contain_text("月別推移")
    expect(page).to_have_url(
        f"{ANALYSIS_URL}?mode=year&year={selected_year}",
        timeout=5000,
    )

    current_month = date.today().strftime("%Y-%m")
    expect(page.locator("#month-input")).to_have_value(current_month)
    page.locator("#month-input").dispatch_event("change")

    expect(page.get_by_test_id("analysis-month-period")).to_contain_text(
        "表示中", timeout=5000
    )
    expect(page.get_by_test_id("analysis-trend-chart")).to_contain_text("日別推移")
    expect(page).to_have_url(f"{ANALYSIS_URL}?month={current_month}", timeout=5000)


def test_analysis_location_filter_updates_chart_and_table_without_changing_url(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    expect(page.get_by_role("heading", name="集計期間")).to_be_visible()
    expect(page.get_by_text("集計対象", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="集計結果")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-chart")).to_be_visible()

    checkboxes = page.locator(".location-checkbox")
    location_count = checkboxes.count()
    assert location_count > 0
    expect(checkboxes).to_have_count(location_count)
    expect(page.get_by_test_id("analysis-selection-summary")).to_have_text(
        f"集計対象 {location_count}件"
    )
    expect(page.get_by_test_id("analysis-no-selection-hint")).to_have_count(0)

    checkbox = checkboxes.first
    location_id = checkbox.get_attribute("value")
    assert location_id is not None

    header = page.locator(f".location-header[data-location-id='{location_id}']")
    expect(checkbox).to_be_checked()
    expect(header).to_be_visible()
    initial_url = page.url

    checkbox.uncheck()

    expect(page.locator(f"#location-{location_id}")).not_to_be_checked(timeout=5000)
    expect(header).to_be_hidden(timeout=5000)
    expect(page.get_by_test_id("analysis-selection-summary")).to_have_text(
        f"集計対象 {location_count - 1}件",
        timeout=5000,
    )
    expect(page.get_by_test_id("analysis-trend-chart")).to_be_visible()
    expect(page).to_have_url(initial_url)


def test_analysis_primary_controls_and_results_remain_reachable_on_narrow_viewport(
    page: Page,
) -> None:
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(ANALYSIS_URL)

    expect(page.locator("#month-input")).to_be_visible()
    expect(page.locator("#year-select")).to_be_visible()
    expect(page.locator(".location-checkbox").first).to_be_visible()
    expect(page.locator("#analysis-table-region")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-chart")).to_be_visible()

    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )

    trend_scroller = page.get_by_test_id("analysis-trend-scroller")
    expect(trend_scroller).to_be_visible()
    assert trend_scroller.evaluate(
        "element => element.scrollWidth > element.clientWidth"
    )

    table_scroller = page.locator("[data-testid='analysis-table']").locator("xpath=..")
    expect(table_scroller).to_be_visible()
    assert table_scroller.evaluate(
        "element => element.scrollWidth > element.clientWidth"
    )
