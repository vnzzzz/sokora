from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"


def _sidebar_viewport_geometry(page: Page) -> dict[str, float]:
    return page.evaluate(
        """() => {
          const sidebar = document.querySelector('.sidebar-panel')
          if (!sidebar) throw new Error('sidebar is missing')
          const rect = sidebar.getBoundingClientRect()
          return {
            top: rect.top,
            bottom: rect.bottom,
            height: rect.height,
            viewportHeight: window.innerHeight,
          }
        }"""
    )


def _assert_sidebar_spans_viewport(page: Page) -> None:
    geometry = _sidebar_viewport_geometry(page)
    assert abs(geometry["top"]) < 1
    assert abs(geometry["bottom"] - geometry["viewportHeight"]) < 1
    assert abs(geometry["height"] - geometry["viewportHeight"]) < 1


def test_sidebar_spans_full_viewport(page: Page) -> None:
    page.goto(BASE_URL)
    sidebar = page.locator(".sidebar-panel")
    expect(sidebar).to_be_visible(timeout=5000)

    _assert_sidebar_spans_viewport(page)

    page.evaluate(
        """() => {
          document.body.style.minHeight = '200vh'
          window.scrollTo(0, Math.floor(window.innerHeight / 2))
        }"""
    )
    page.wait_for_function("window.scrollY > 0")

    _assert_sidebar_spans_viewport(page)


def test_sidebar_contents_scroll_in_short_viewport_without_shrinking(page: Page) -> None:
    page.set_viewport_size({"width": 1280, "height": 360})
    page.goto(BASE_URL)

    scroll_area = page.locator(".sidebar-panel > div")
    api_link = page.locator('.sidebar-nav-link[href="/docs"]')
    expect(scroll_area).to_be_visible(timeout=5000)
    expect(api_link).to_be_attached()

    overflow = scroll_area.evaluate(
        "element => ({clientHeight: element.clientHeight, scrollHeight: element.scrollHeight})"
    )
    assert overflow["scrollHeight"] > overflow["clientHeight"]

    api_link.scroll_into_view_if_needed()
    api_box = api_link.bounding_box()
    assert api_box is not None
    viewport_height = page.evaluate("window.innerHeight")
    assert api_box["y"] >= 0
    assert api_box["y"] + api_box["height"] <= viewport_height + 1
