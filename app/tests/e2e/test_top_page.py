import pytest
from playwright.sync_api import Page, Request, expect

TOP_URL = "http://localhost:8000"


def _shell_geometry(page: Page) -> dict[str, float]:
    return page.evaluate(
        """() => {
          const sidebar = document.querySelector('.sidebar-panel')
          const main = document.querySelector('.app-main')
          if (!sidebar || !main) throw new Error('application shell is missing')
          const sidebarRect = sidebar.getBoundingClientRect()
          const mainRect = main.getBoundingClientRect()
          return {
            sidebarWidth: sidebarRect.width,
            sidebarRight: sidebarRect.right,
            mainLeft: mainRect.left,
          }
        }"""
    )


def _assert_shell_geometry(page: Page, expected_sidebar_width: float) -> None:
    geometry = _shell_geometry(page)
    assert abs(geometry["sidebarWidth"] - expected_sidebar_width) < 1
    assert abs(geometry["mainLeft"] - expected_sidebar_width) < 1
    assert abs(geometry["sidebarRight"] - geometry["mainLeft"]) < 1


def _sample_sidebar_frames(page: Page, count: int = 6) -> list[list[dict[str, float | str]]]:
    return page.evaluate(
        """count => new Promise(resolve => {
          const frames = []
          function sample() {
            const links = Array.from(document.querySelectorAll('.sidebar-nav-link'))
            frames.push(links.map(link => {
              const rect = link.getBoundingClientRect()
              return {
                href: link.getAttribute('href'),
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
              }
            }))
            if (frames.length >= count) resolve(frames)
            else requestAnimationFrame(sample)
          }
          requestAnimationFrame(sample)
        })""",
        count,
    )


def _assert_sidebar_frames_stable(
    frames: list[list[dict[str, float | str]]],
) -> None:
    assert frames
    baseline = frames[0]
    assert baseline
    for frame in frames[1:]:
        assert len(frame) == len(baseline)
        for expected, actual in zip(baseline, frame, strict=True):
            assert actual["href"] == expected["href"]
            for key in ("x", "y", "width", "height"):
                assert isinstance(actual[key], float | int)
                assert isinstance(expected[key], float | int)
                assert abs(actual[key] - expected[key]) < 0.5


def test_top_calendar_htmx_navigation_and_day_detail(page: Page) -> None:
    page.goto(TOP_URL)
    expect(page.locator("h2")).to_have_text("勤怠確認")

    calendar = page.locator("#calendar-area")
    detail = page.locator("#detail-area")
    first_cell = calendar.locator(".calendar-cell[data-date]").first
    expect(first_cell).to_be_visible(timeout=5000)
    expect(calendar.locator(".selected-date")).to_have_count(1, timeout=5000)

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
    expect(calendar.locator(".selected-date")).to_have_count(1)

    current_button = calendar.locator(".btn-group .btn-neutral")
    current_button.click()
    expect(month_label).to_have_text(initial_month, timeout=5000)
    expect(calendar.locator(".selected-date")).to_have_count(1)


@pytest.mark.parametrize(
    ("stored_state", "expected_width", "labels_visible"),
    [("true", 200, True), ("false", 64, False)],
)
def test_sidebar_persisted_state_is_applied_without_alpine_layout_dependency(
    page: Page,
    stored_state: str,
    expected_width: float,
    labels_visible: bool,
) -> None:
    page.add_init_script(
        f"localStorage.setItem('sidebarOpen', '{stored_state}')"
    )
    page.route(
        "**/assets/js/alpine.min.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body="",
        ),
    )

    page.goto(TOP_URL)

    sidebar = page.locator(".sidebar-panel")
    main = page.locator(".app-main")
    label = page.locator(".sidebar-label").first
    expect(sidebar).to_be_visible(timeout=5000)
    expect(main).to_be_visible(timeout=5000)
    _assert_shell_geometry(page, expected_width)
    assert sidebar.evaluate("element => getComputedStyle(element).transitionProperty") == "none"
    assert main.evaluate("element => getComputedStyle(element).transitionProperty") == "none"
    if labels_visible:
        expect(label).to_be_visible()
    else:
        expect(label).to_be_hidden()

    page.locator('.sidebar-nav-link[href="/analysis"]').click()
    page.wait_for_url(f"{TOP_URL}/analysis")

    sidebar = page.locator(".sidebar-panel")
    main = page.locator(".app-main")
    expect(sidebar).to_be_visible(timeout=5000)
    _assert_shell_geometry(page, expected_width)
    assert sidebar.evaluate("element => getComputedStyle(element).transitionProperty") == "none"
    assert main.evaluate("element => getComputedStyle(element).transitionProperty") == "none"


@pytest.mark.parametrize("stored_state", ["true", "false"])
def test_sidebar_links_remain_geometrically_stable_across_full_navigation(
    page: Page,
    stored_state: str,
) -> None:
    page.add_init_script(
        f"localStorage.setItem('sidebarOpen', '{stored_state}')"
    )
    page.goto(TOP_URL)
    page.wait_for_load_state("networkidle")

    source_frames = _sample_sidebar_frames(page)
    _assert_sidebar_frames_stable(source_frames)
    source_geometry = source_frames[-1]

    page.locator('.sidebar-nav-link[href="/analysis"]').click()
    page.wait_for_url(f"{TOP_URL}/analysis")
    destination_frames = _sample_sidebar_frames(page)
    _assert_sidebar_frames_stable(destination_frames)
    destination_geometry = destination_frames[0]

    assert len(source_geometry) == len(destination_geometry)
    for source, destination in zip(source_geometry, destination_geometry, strict=True):
        assert source["href"] == destination["href"]
        for key in ("x", "y", "width", "height"):
            assert isinstance(source[key], float | int)
            assert isinstance(destination[key], float | int)
            assert abs(source[key] - destination[key]) < 0.5


def test_sidebar_manual_toggle_animates_and_persists_without_navigation_transition(
    page: Page,
) -> None:
    page.add_init_script("localStorage.setItem('sidebarOpen', 'true')")
    page.goto(TOP_URL)

    root = page.locator("html")
    sidebar = page.locator(".sidebar-panel")
    main = page.locator(".app-main")
    toggle = page.locator("[data-sidebar-toggle]")
    expect(toggle).to_be_visible(timeout=5000)
    _assert_shell_geometry(page, 200)
    assert sidebar.evaluate("element => getComputedStyle(element).transitionProperty") == "none"
    assert main.evaluate("element => getComputedStyle(element).transitionProperty") == "none"

    toggle.click()
    expect(root).to_have_attribute("data-sidebar-open", "false")
    expect(root).to_have_class("sidebar-animating")
    assert "width" in sidebar.evaluate(
        "element => getComputedStyle(element).transitionProperty"
    )
    assert "margin-left" in main.evaluate(
        "element => getComputedStyle(element).transitionProperty"
    )
    page.wait_for_function(
        "!document.documentElement.classList.contains('sidebar-animating')"
    )
    _assert_shell_geometry(page, 64)
    assert page.evaluate("localStorage.getItem('sidebarOpen')") == "false"

    page.reload()
    expect(root).to_have_attribute("data-sidebar-open", "false")
    _assert_shell_geometry(page, 64)
    assert sidebar.evaluate("element => getComputedStyle(element).transitionProperty") == "none"
    assert main.evaluate("element => getComputedStyle(element).transitionProperty") == "none"


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
