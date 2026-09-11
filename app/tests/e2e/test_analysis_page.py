from datetime import date, timedelta

from playwright.sync_api import Page, expect

ANALYSIS_URL = "http://localhost:8000/analysis"


def test_analysis_month_change_updates_dom_and_history(page: Page) -> None:
    page.goto(ANALYSIS_URL)
    expect(page).to_have_title("Sokora - 勤怠集計")
    initial_month = page.locator("#month-input").input_value()
    expect(page.get_by_test_id("analysis-coverage-chart")).to_be_visible()
    expect(page.get_by_role("link", name="月次")).to_have_attribute(
        "aria-current", "page"
    )
    expect(page.get_by_role("link", name="年度")).to_be_visible()

    first_of_month = date.today().replace(day=1)
    previous_month = first_of_month - timedelta(days=1)
    target_month = previous_month.strftime("%Y-%m")

    month_input = page.locator("#month-input")
    month_input.fill(target_month)
    month_input.dispatch_event("change")

    expect(page).to_have_url(
        f"{ANALYSIS_URL}?month={target_month}",
        timeout=5000,
    )
    expect(page.locator("#month-input")).to_have_value(target_month)
    expect(page.get_by_test_id("analysis-coverage-chart")).to_be_visible()
    expect(page.locator("#analysis-total-series")).to_be_checked()
    expect(page.locator("#analysis-group-select")).to_have_value("")
    expect(page.locator("#analysis-user-type-select")).to_have_value("")

    page.go_back()
    expect(page).to_have_url(ANALYSIS_URL, timeout=5000)
    expect(page.locator("#month-input")).to_have_value(
        initial_month,
        timeout=5000,
    )


def test_analysis_month_and_fiscal_year_are_separate_views(page: Page) -> None:
    page.goto(ANALYSIS_URL)

    month_tab = page.get_by_role("link", name="月次")
    year_tab = page.get_by_role("link", name="年度")

    expect(month_tab).to_have_attribute("aria-current", "page")
    expect(year_tab).to_be_visible()
    expect(page.locator("#month-input")).to_be_visible()
    expect(page.locator("#year-select")).to_have_count(0)
    expect(page.get_by_test_id("analysis-day-trigger").first).to_be_visible()

    year_tab.click()

    expect(page.get_by_role("link", name="年度")).to_have_attribute(
        "aria-current", "page", timeout=5000
    )
    expect(page.locator("#year-select")).to_be_visible()
    expect(page.locator("#month-input")).to_have_count(0)
    selected_year = page.locator("#year-select").input_value()
    expect(page.get_by_test_id("analysis-coverage-chart")).to_be_visible()
    expect(page.locator("#analysis-total-series")).to_be_checked()
    expect(page.get_by_test_id("analysis-day-trigger")).to_have_count(0)
    expect(page.locator("#analysis-day-detail")).to_have_count(0)
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
    expect(page.get_by_test_id("analysis-coverage-chart")).to_be_visible()
    expect(page.locator("#analysis-total-series")).to_be_checked()
    expect(page.get_by_test_id("analysis-day-trigger").first).to_be_visible()
    expect(page).to_have_url(
        f"{ANALYSIS_URL}?month={current_month}",
        timeout=5000,
    )


def test_analysis_target_selectors_update_one_chart_without_changing_url(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    group_select = page.locator("#analysis-group-select")
    user_type_select = page.locator("#analysis-user-type-select")
    expect(group_select).to_be_visible()
    expect(user_type_select).to_be_visible()
    expect(page.get_by_test_id("analysis-chart-target")).to_have_text(
        "全組織 / 全社員種別"
    )
    expect(page.get_by_test_id("analysis-chart-scroller")).to_have_count(1)
    initial_url = page.url

    group_values = group_select.locator("option").evaluate_all(
        "options => options.map(option => option.value).filter(Boolean)"
    )
    user_type_values = user_type_select.locator("option").evaluate_all(
        "options => options.map(option => option.value).filter(Boolean)"
    )
    assert group_values
    assert user_type_values

    group_value = group_values[0]
    user_type_value = user_type_values[0]
    group_select.select_option(group_value)
    expect(page.get_by_test_id("analysis-chart-target")).to_contain_text(
        group_value,
        timeout=5000,
    )

    user_type_select.select_option(user_type_value)
    target = page.get_by_test_id("analysis-chart-target")
    expect(target).to_contain_text(group_value, timeout=5000)
    expect(target).to_contain_text(user_type_value, timeout=5000)
    expect(page.get_by_test_id("analysis-chart-scroller")).to_have_count(1)
    expect(page).to_have_url(initial_url)


def test_analysis_series_filter_defaults_to_total_and_supports_bulk_actions(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    expect(page.get_by_role("heading", name="表示条件")).to_be_visible()
    expect(page.get_by_text("表示系列", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="人数推移")).to_be_visible()
    expect(page.get_by_test_id("analysis-coverage-chart")).to_be_visible()
    accessible_data = page.get_by_test_id("analysis-chart-accessible-data")
    expect(accessible_data).to_contain_text("全合計")

    filter_details = page.locator("#analysis-location-filter details")
    expect(filter_details).not_to_have_attribute("open", "")
    filter_details.locator("summary").click()

    total_checkbox = page.locator("#analysis-total-series")
    expect(total_checkbox).to_be_checked()

    checkboxes = page.locator(".location-checkbox")
    location_count = checkboxes.count()
    assert location_count > 0
    expect(checkboxes.first).to_be_visible()
    for index in range(location_count):
        expect(checkboxes.nth(index)).not_to_be_checked()

    checkbox = checkboxes.first
    location_id = checkbox.get_attribute("value")
    assert location_id is not None
    location_name = page.locator(
        f"label[for='location-{location_id}'] span"
    ).inner_text()
    initial_url = page.url

    checkbox.check()

    expect(page.locator(f"#location-{location_id}")).to_be_checked(timeout=5000)
    expect(total_checkbox).to_be_checked()
    expect(accessible_data).to_contain_text(location_name, timeout=5000)
    expect(page.get_by_test_id("analysis-chart-scroller")).to_have_count(1)
    expect(page).to_have_url(initial_url)

    page.get_by_role("button", name="全選択", exact=True).click()
    expect(total_checkbox).to_be_checked()
    for index in range(location_count):
        expect(checkboxes.nth(index)).to_be_checked(timeout=5000)
    expect(page.get_by_test_id("analysis-coverage-chart")).to_be_visible()
    expect(page.get_by_test_id("analysis-chart-scroller")).to_have_count(1)
    expect(page).to_have_url(initial_url)

    page.get_by_role("button", name="全解除", exact=True).click()
    expect(total_checkbox).not_to_be_checked()
    for index in range(location_count):
        expect(checkboxes.nth(index)).not_to_be_checked(timeout=5000)
    expect(page.get_by_test_id("analysis-no-selection-hint")).to_be_visible(
        timeout=5000
    )
    expect(page.get_by_test_id("analysis-coverage-chart")).to_have_count(0)
    expect(page).to_have_url(initial_url)


def test_analysis_month_axis_labels_load_visible_day_detail_without_navigation(
    page: Page,
) -> None:
    page.goto(ANALYSIS_URL)

    trigger = page.get_by_test_id("analysis-day-trigger").first
    expect(trigger).to_be_visible()
    expect(trigger.locator("text")).to_have_text("1")
    expect(trigger.locator("xpath=ancestor::svg")).to_have_count(1)
    day = trigger.get_attribute("data-analysis-day")
    assert day is not None
    initial_url = page.url

    trigger.click()

    expect(trigger).to_have_attribute("aria-current", "date")
    detail = page.locator("#analysis-day-detail")
    expect(detail.locator("#day-detail-container")).to_be_visible(timeout=5000)
    expect(detail).to_contain_text(
        f"{day}の勤怠情報",
        timeout=5000,
    )
    expect(detail).to_be_in_viewport(timeout=5000)
    expect(page).to_have_url(initial_url)


def test_analysis_primary_controls_and_chart_remain_reachable_on_narrow_viewport(
    page: Page,
) -> None:
    page.set_viewport_size({"width": 390, "height": 800})
    page.goto(ANALYSIS_URL)

    expect(page.get_by_role("link", name="月次")).to_be_visible()
    expect(page.get_by_role("link", name="年度")).to_be_visible()
    expect(page.locator("#month-input")).to_be_visible()
    expect(page.locator("#analysis-group-select")).to_be_visible()
    expect(page.locator("#analysis-user-type-select")).to_be_visible()
    expect(page.get_by_text("表示系列", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="人数推移")).to_be_visible()

    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )

    scroller = page.get_by_test_id("analysis-chart-scroller")
    expect(scroller).to_be_visible()
    assert scroller.evaluate("element => element.scrollWidth > element.clientWidth")
    expect(page.get_by_test_id("analysis-day-trigger").first).to_be_visible()

    filter_details = page.locator("#analysis-location-filter details")
    filter_details.locator("summary").click()
    expect(page.locator("#analysis-total-series")).to_be_checked()
    expect(page.locator(".location-checkbox").first).to_be_visible()
