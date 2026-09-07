import time

from playwright.sync_api import Page, expect

GROUPS_URL = "http://localhost:8000/groups"


def test_group_crud_lifecycle(page: Page) -> None:
    suffix = time.time_ns()
    initial_name = f"E2Eグループ_{suffix}"
    updated_name = f"E2Eグループ更新_{suffix}"

    page.goto(GROUPS_URL)
    expect(page.locator("h2")).to_have_text("グループ管理")

    page.get_by_role("button", name="グループ追加").click()
    add_modal = page.locator("#add-group")
    expect(add_modal).to_be_visible()
    add_modal.locator('input[name="name"]').fill(initial_name)
    add_modal.locator('input[name="order"]').fill("999")
    add_modal.get_by_role("button", name="登録").click()

    expect(add_modal).to_be_hidden()
    row = page.locator("#group-table-body tr").filter(has_text=initial_name)
    expect(row).to_be_visible()
    row_id = row.get_attribute("id")
    assert row_id is not None and row_id.startswith("group-row-")
    group_id = row_id.removeprefix("group-row-")

    row.get_by_role("button", name="編集").click()
    edit_modal = page.locator(f"#edit-group-{group_id}")
    expect(edit_modal).to_be_visible()
    edit_modal.locator('input[name="name"]').fill(updated_name)
    edit_modal.get_by_role("button", name="更新").click()

    expect(edit_modal).to_be_hidden()
    updated_row = page.locator(f"#group-row-{group_id}")
    expect(updated_row).to_contain_text(updated_name)
    expect(updated_row).not_to_contain_text(initial_name)

    updated_row.get_by_role("button", name="削除").click()
    delete_modal = page.locator(f"#group-delete-modal-{group_id}")
    expect(delete_modal).to_be_visible()
    delete_modal.get_by_role("button", name="削除").click()

    expect(delete_modal).to_be_hidden()
    expect(page.locator(f"#group-row-{group_id}")).not_to_be_visible()
