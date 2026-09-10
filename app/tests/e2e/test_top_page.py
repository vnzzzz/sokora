from playwright.sync_api import Page, Request, expect

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


def test_sidebar_persisted_state_is_applied_before_alpine_boot(page: Page) -> None:
    page.add_init_script("localStorage.setItem('sidebarOpen', 'false')")
    page.route(
        "**/assets/js/alpine.min.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body="",
        ),
    )

    page.goto(TOP_URL)

    sidebar = page.locator("aside")
    main = page.locator(".app-main")
    expect(sidebar).to_be_visible(timeout=5000)
    expect(main).to_be_visible(timeout=5000)

    sidebar_box = sidebar.bounding_box()
    main_box = main.bounding_box()
    assert sidebar_box is not None
    assert main_box is not None
    assert abs(sidebar_box["width"] - 64) < 1
    assert abs(main_box["x"] - 64) < 1


def test_calendar_selection_highlight_does_not_resize_table(page: Page) -> None:
    page.goto(TOP_URL)

    calendar = page.locator("#calendar-area")
    table = calendar.locator("table")
    expect(calendar.locator(".selected-date")).to_have_count(1, timeout=5000)
    expect(table).to_be_visible(timeout=5000)

    selected_height = table.evaluate(
        "element => element.getBoundingClientRect().height"
    )
    calendar.locator(".selected-date, .selected-column").evaluate_all(
        "elements => elements.forEach("
        "element => element.classList.remove('selected-date', 'selected-column'))"
    )
    unselected_height = table.evaluate(
        "element => element.getBoundingClientRect().height"
    )

    assert abs(selected_height - unselected_height) < 0.5


def test_calendar_cell_click_requests_day_detail_once(page: Page) -> None:
    page.goto(TOP_URL)

    calendar = page.locator("#calendar-area")
    detail = page.locator("#detail-area")
    expect(calendar.locator(".selected-date")).to_have_count(1, timeout=5000)
    expect(detail).to_contain_text("の勤怠情報", timeout=5000)

    target = calendar.locator("th.calendar-cell[data-date]").nth(1)
    target_date = target.get_attribute("data-date")
    assert target_date is not None

    detail_requests: list[str] = []

    def record_day_detail_request(request: Request) -> None:
        if f"/calendar/day/{target_date}" in request.url:
            detail_requests.append(request.url)

    page.on("request", record_day_detail_request)
    target.click()
    expect(detail).to_contain_text(f"{target_date}の勤怠情報", timeout=5000)
    page.wait_for_load_state("networkidle")

    assert len(detail_requests) == 1
