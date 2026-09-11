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
