from datetime import date, timedelta

from playwright.sync_api import Page, expect

ANALYSIS_URL = "http://localhost:8000/analysis"


def test_analysis_month_change_updates_dom_and_history(page: Page) -> None:
    page.goto(ANALYSIS_URL)
    expect(page).to_have_title("Sokora - 勤怠集計")
    initial_label = page.locator(".analysis-period-label").inner_text()
    expect(page.locator("[data-testid='analysis-table']")).to_be_visible()
    expect(page.get_by_role("link", name="月次")).to_have_attribute(
        "aria-current", "page"
    )
    expect(page.get_by_role("link", name="年度")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-plot")).to_be_visible()
    expect(page.get_by_test_id("analysis-group-coverage")).to_be_visible()

    first_of_month = date.today().replace(day=1)
    previous_month = first_of_month - timedelta(days=1)
    target_month = previous_month.strftime("%Y-%m")
    target_label = f"{previous_month.year}年{previous_month.month}月"

    month_input = page.locator("#month-input")
    month_input.fill(target_month)
    month_input.dispatch_event("change")

    expect(page.locator(".analysis-period-label")).to_contain_text(
        target_label,
        timeout=5000,
    )
    expect(page).to_have_url(
        f"{ANALYSIS_URL}?month={target_month}",
        timeout=5000,
    )
    expect(page.locator("#month-input")).to_have_value(target_month)
    expect(page.get_by_role("link", name="月次")).to_have_attribute(
        "aria-current", "page"
    )
    expect(page.locator("[data-testid='analysis-table']")).to_be_visible()
    expect(page.get_by_test_id("analysis-group-coverage")).to_be_visible()

    page.go_back()
    expect(page).to_have_url(ANALYSIS_URL, timeout=5000)
    expect(page.locator(".analysis-period-label")).to_have_text(
        initial_label, timeout=5000
    )


def test_analysis_month_and_fiscal_year_are_separate_views(page: Page) -> None:
    page.goto(ANALYSIS_URL)

    month_tab = page.get_by_role("link", name="月次")
    year_tab = page.get_by_role("link", name="年度")
    expect(month_tab).to_have_attribute("aria-current", "page")
    expect(year_tab).to_be_visible()
    expect(page.locator("#month-input")).to_be_visible()
    expect(page.locator("#year-select")).to_have_count(0)

    year_tab.click()

    expect(page.get_by_role("link", name="年度")).to_have_attribute(
        "aria-current", "page", timeout=5000
    )
    expect(page.locator("#year-select")).to_be_visible()
    expect(page.locator("#month-input")).to_have_count(0)
    selected_year = page.locator("#year-select").input_value()
    expect(page.locator(".analysis-period-label")).to_contain_text("年度")
    expect(page.get_by_test_id("analysis-trend-chart")).to_contain_text(
        "月ごとの延べ登録日数"
    )
    expect(page.get_by_test_id("analysis-group-coverage")).to_be_visible()
    expect(page).to_have_url(
        f"{ANALYSIS_URL}?mode=year&year={selected_year}",
        timeout=5000,
    )

    page.get_by_role("link", name="月次").click()

    current_month = date.today().strftime("%Y-%m")
    expect(page.get_by_role("link", name="月次")).to_have_attribute(
        "aria-current", "page", timeout=5000
    )
    expect(page.locator("#month-input")).to_have_value(current_month)
    expect(page.locator("#year-select")).to_have_count(0)
    expect(page.get_by_test_id("analysis-trend-chart")).to_contain_text(
        "日ごとの延べ登録日数"
    )
    expect(page).to_have_url(f"{ANALYSIS_URL}?month={current_month}", timeout=5000)


def test_analysis_location_filter_updates_all_results_without_changing_url(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    expect(page.get_by_role("heading", name="表示条件")).to_be_visible()
    expect(page.get_by_text("集計対象", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="概要")).to_be_visible()
    expect(page.get_by_role("heading", name="配置状況")).to_be_visible()
    expect(page.get_by_text("組織別", exact=True)).to_be_visible()
    expect(page.get_by_text("社員種別別", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="社員別明細")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-plot")).to_be_visible()
    expect(page.get_by_test_id("analysis-group-coverage")).to_be_visible()
    expect(page.get_by_test_id("analysis-user-type-coverage")).to_be_visible()

    filter_details = page.locator("#analysis-location-filter details")
    expect(filter_details).not_to_have_attribute("open", "")
    filter_details.locator("summary").click()

    checkboxes = page.locator(".location-checkbox")
    location_count = checkboxes.count()
    assert location_count > 0
    expect(checkboxes.first).to_be_visible()
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
    expect(page.get_by_test_id("analysis-group-coverage")).to_be_visible()
    expect(page.get_by_test_id("analysis-user-type-coverage")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-plot")).to_be_visible()
    expect(page).to_have_url(initial_url)


def test_analysis_primary_controls_and_results_remain_reachable_on_narrow_viewport(
    page: Page,
) -> None:
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(ANALYSIS_URL)

    expect(page.get_by_role("link", name="月次")).to_be_visible()
    expect(page.get_by_role("link", name="年度")).to_be_visible()
    expect(page.locator("#month-input")).to_be_visible()
    expect(page.get_by_text("集計対象", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="概要")).to_be_visible()
    expect(page.get_by_role("heading", name="配置状況")).to_be_visible()
    expect(page.get_by_role("heading", name="社員別明細")).to_be_visible()
    expect(page.get_by_test_id("analysis-trend-plot")).to_be_visible()
    expect(page.get_by_test_id("analysis-group-coverage")).to_be_visible()

    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )

    coverage_scroller = page.get_by_test_id("analysis-group-coverage-scroller")
    expect(coverage_scroller).to_be_visible()
    assert coverage_scroller.evaluate(
        "element => element.scrollWidth > element.clientWidth"
    )

    trend_scroller = page.get_by_test_id("analysis-trend-scroller")
    expect(trend_scroller).to_be_visible()
    assert trend_scroller.evaluate(
        "element => element.scrollWidth > element.clientWidth"
    )

    filter_details = page.locator("#analysis-location-filter details")
    filter_details.locator("summary").click()
    expect(page.locator(".location-checkbox").first).to_be_visible()

    table_scroller = page.locator("[data-testid='analysis-table']").locator("xpath=..")
    expect(table_scroller).to_be_visible()
    assert table_scroller.evaluate(
        "element => element.scrollWidth > element.clientWidth"
    )
