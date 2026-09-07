from datetime import date, timedelta

from playwright.sync_api import Page, expect

ATTENDANCE_WEEKLY_URL = "http://localhost:8000/attendance/weekly"


def _future_monday() -> date:
    target = date.today() + timedelta(days=90)
    return target + timedelta(days=(7 - target.weekday()) % 7)


def test_attendance_modal_create_update_delete_refreshes_week(page: Page) -> None:
    monday = _future_monday()
    page.goto(f"{ATTENDANCE_WEEKLY_URL}?week={monday.isoformat()}")

    cell = page.locator("#calendar td.attendance-cell").first
    expect(cell).to_be_visible()
    expect(cell).to_have_attribute("data-has-data", "false")

    user_id = cell.get_attribute("data-user-id")
    target_date = cell.get_attribute("data-date")
    assert user_id
    assert target_date

    cell.click()
    modal = page.locator(f"#attendance-modal-{user_id}-{target_date}")
    expect(modal).to_be_visible()

    location_buttons = modal.locator(".location-select-btn")
    expect(location_buttons.first).to_be_visible()
    assert location_buttons.count() >= 2

    first_location = location_buttons.nth(0)
    first_location_name = first_location.inner_text().strip()
    first_location.click()
    modal.get_by_role("button", name="登録").click()

    expect(modal).to_be_hidden()
    refreshed_cell = page.locator(
        f'#calendar td.attendance-cell[data-user-id="{user_id}"]'
        f'[data-date="{target_date}"]'
    )
    expect(refreshed_cell).to_have_attribute("data-has-data", "true", timeout=5000)
    expect(refreshed_cell).to_have_attribute(
        "data-location", first_location_name, timeout=5000
    )
    expect(refreshed_cell).to_contain_text(first_location_name)

    refreshed_cell.click()
    edit_modal = page.locator(f"#attendance-modal-{user_id}-{target_date}")
    expect(edit_modal).to_be_visible()

    second_location = edit_modal.locator(".location-select-btn").nth(1)
    second_location_name = second_location.inner_text().strip()
    assert second_location_name != first_location_name
    second_location.click()
    edit_modal.get_by_role("button", name="更新").click()

    expect(edit_modal).to_be_hidden()
    expect(refreshed_cell).to_have_attribute(
        "data-location", second_location_name, timeout=5000
    )
    expect(refreshed_cell).to_contain_text(second_location_name)

    refreshed_cell.click()
    delete_modal = page.locator(f"#attendance-modal-{user_id}-{target_date}")
    expect(delete_modal).to_be_visible()
    delete_modal.get_by_role("button", name="削除").click()

    expect(delete_modal).to_be_hidden()
    expect(refreshed_cell).to_have_attribute("data-has-data", "false", timeout=5000)
    expect(refreshed_cell).to_have_attribute("data-location", "", timeout=5000)
    expect(refreshed_cell).to_be_empty()
