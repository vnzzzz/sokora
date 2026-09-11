import base64
import json

from itsdangerous import TimestampSigner
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"


def _development_session_cookie(session: dict[str, object]) -> str:
    payload = base64.b64encode(json.dumps(session).encode("utf-8"))
    return TimestampSigner("dev-session-secret").sign(payload).decode("utf-8")


def test_logout_control_responds_on_first_hover_without_tooltip(page: Page) -> None:
    """logout controlはicon上を含む初回hoverから反応し、補助tooltipを表示しない。"""
    page.context.add_cookies(
        [
            {
                "name": "session",
                "value": _development_session_cookie(
                    {
                        "auth": {
                            "method": "oidc",
                            "subject": "e2e-user",
                            "username": "e2e-user",
                        }
                    }
                ),
                "url": BASE_URL,
            }
        ]
    )
    page.goto(BASE_URL)

    logout_button = page.get_by_test_id("logout-button")
    logout_icon = page.get_by_test_id("logout-icon")
    expect(logout_button).to_be_visible()
    expect(logout_icon).to_be_visible()

    logout_form = logout_button.locator("xpath=..")
    expect(logout_form).not_to_have_class("tooltip")
    assert logout_form.get_attribute("data-tip") is None

    before_hover = logout_button.evaluate(
        "element => getComputedStyle(element).backgroundColor"
    )
    icon_box = logout_icon.bounding_box()
    assert icon_box is not None
    icon_x = icon_box["x"] + icon_box["width"] / 2
    icon_y = icon_box["y"] + icon_box["height"] / 2
    page.mouse.move(icon_x, icon_y)

    hit_is_button = page.evaluate(
        """([x, y]) => {
          const button = document.querySelector('[data-testid="logout-button"]')
          const hit = document.elementFromPoint(x, y)
          return Boolean(button && hit === button)
        }""",
        [icon_x, icon_y],
    )
    after_hover = logout_button.evaluate(
        "element => getComputedStyle(element).backgroundColor"
    )

    assert hit_is_button is True
    assert after_hover != before_hover
