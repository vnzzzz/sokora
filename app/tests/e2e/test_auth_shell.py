import base64
import json

from itsdangerous import TimestampSigner
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"


def _development_session_cookie(session: dict[str, object]) -> str:
    payload = base64.b64encode(json.dumps(session).encode("utf-8"))
    return TimestampSigner("dev-session-secret").sign(payload).decode("utf-8")


def test_logout_control_responds_on_first_hover_without_tooltip(page: Page) -> None:
    """logout controlはicon上でも同じhover feedbackとclick surfaceを維持する。"""
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

    form_box = logout_form.bounding_box()
    button_box = logout_button.bounding_box()
    icon_box = logout_icon.bounding_box()
    assert form_box is not None
    assert button_box is not None
    assert icon_box is not None
    assert abs(form_box["width"] - button_box["width"]) < 0.5
    assert abs(form_box["height"] - button_box["height"]) < 0.5

    button_center_x = button_box["x"] + button_box["width"] / 2
    button_center_y = button_box["y"] + button_box["height"] / 2
    icon_center_x = icon_box["x"] + icon_box["width"] / 2
    icon_center_y = icon_box["y"] + icon_box["height"] / 2
    assert abs(button_center_x - icon_center_x) < 0.5
    assert abs(button_center_y - icon_center_y) < 0.5

    before_hover = logout_button.evaluate(
        "element => getComputedStyle(element).backgroundColor"
    )

    ring_x = form_box["x"] + 4
    ring_y = form_box["y"] + form_box["height"] / 2
    page.mouse.move(ring_x, ring_y)
    ring_hover = logout_button.evaluate(
        "element => getComputedStyle(element).backgroundColor"
    )
    assert logout_form.evaluate("element => element.matches(':hover')") is True
    assert ring_hover != before_hover

    # button中心とicon中心が一致することを上で確認したうえで、pointer
    # interactionを担うbuttonの中心へ移動する。
    page.mouse.move(button_center_x, button_center_y)

    icon_hover = logout_button.evaluate(
        "element => getComputedStyle(element).backgroundColor"
    )
    interaction_state = page.evaluate(
        """([x, y]) => {
          const form = document.querySelector('.logout-control')
          const button = document.querySelector('[data-testid="logout-button"]')
          const hit = document.elementFromPoint(x, y)
          return {
            formHovered: Boolean(form && form.matches(':hover')),
            hitInsideButton: Boolean(
              button && hit && (hit === button || button.contains(hit))
            ),
          }
        }""",
        [button_center_x, button_center_y],
    )

    assert interaction_state["formHovered"] is True
    assert interaction_state["hitInsideButton"] is True
    assert icon_hover == ring_hover
