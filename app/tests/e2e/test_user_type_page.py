import time

from playwright.sync_api import Page, expect

USER_TYPES_URL = "http://localhost:8000/user-types"


def test_user_type_crud_lifecycle(page: Page) -> None:
    suffix = time.time_ns()
    initial_name = f"E2Eテスト社員種別_{suffix}"
    updated_name = f"E2Eテスト社員種別更新_{suffix}"

    page.goto(USER_TYPES_URL)
    expect(page.locator("h2")).to_have_text("社員種別管理")

    page.get_by_role("button", name="社員種別追加").click()
    add_modal = page.locator("#add-user-type")
    expect(add_modal).to_be_visible()
    add_modal.locator('input[name="name"]').fill(initial_name)
    add_modal.locator('input[name="order"]').fill("999")
    add_modal.get_by_role("button", name="登録").click()

    expect(add_modal).to_be_hidden()
    row = page.locator("#user-type-table-body tr").filter(has_text=initial_name)
    expect(row).to_be_visible()
    row_id = row.get_attribute("id")
    assert row_id is not None and row_id.startswith("user-type-row-")
    user_type_id = row_id.removeprefix("user-type-row-")

    row.get_by_role("button", name="編集").click()
    edit_modal = page.locator(f"#edit-user-type-{user_type_id}")
    expect(edit_modal).to_be_visible()
    edit_modal.locator('input[name="name"]').fill(updated_name)
    edit_modal.get_by_role("button", name="更新").click()

    expect(edit_modal).to_be_hidden()
    updated_row = page.locator(f"#user-type-row-{user_type_id}")
    expect(updated_row).to_contain_text(updated_name)
    expect(updated_row).not_to_contain_text(initial_name)

    updated_row.get_by_role("button", name="削除").click()
    delete_modal = page.locator(f"#user-type-delete-modal-{user_type_id}")
    expect(delete_modal).to_be_visible()
    delete_modal.get_by_role("button", name="削除").click()

    expect(delete_modal).to_be_hidden()
    expect(page.locator(f"#user-type-row-{user_type_id}")).not_to_be_visible()
