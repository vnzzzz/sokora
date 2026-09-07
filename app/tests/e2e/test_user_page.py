import time

from playwright.sync_api import Page, expect

USERS_URL = "http://localhost:8000/users"


def test_user_crud_lifecycle_uses_real_master_ids(page: Page) -> None:
    suffix = time.time_ns()
    user_id = f"e2e_{suffix}"
    initial_name = f"E2E社員_{suffix}"
    updated_name = f"E2E社員更新_{suffix}"

    page.goto(USERS_URL)
    expect(page.locator("h2")).to_have_text("社員管理")

    page.get_by_role("button", name="社員追加").click()
    add_modal = page.locator("#user-modal-new")
    expect(add_modal).to_be_visible()

    group_select = add_modal.locator('select[name="group_id"]')
    user_type_select = add_modal.locator('select[name="user_type_id"]')
    first_group = group_select.locator("option").nth(1)
    first_user_type = user_type_select.locator("option").nth(1)
    first_group_id = first_group.get_attribute("value")
    first_user_type_id = first_user_type.get_attribute("value")
    assert first_group_id
    assert first_user_type_id

    add_modal.locator('input[name="id"]').fill(user_id)
    add_modal.locator('input[name="username"]').fill(initial_name)
    group_select.select_option(value=first_group_id)
    user_type_select.select_option(value=first_user_type_id)
    add_modal.get_by_role("button", name="登録").click()

    expect(add_modal).to_be_hidden()
    row = page.locator(f"#user-row-{user_id}")
    expect(row).to_be_visible()
    expect(row).to_contain_text(initial_name)

    row.get_by_role("button", name="編集").click()
    edit_modal = page.locator(f"#user-modal-{user_id}")
    expect(edit_modal).to_be_visible()

    edit_group_select = edit_modal.locator('select[name="group_id"]')
    edit_user_type_select = edit_modal.locator('select[name="user_type_id"]')
    second_group = edit_group_select.locator("option").nth(2)
    second_user_type = edit_user_type_select.locator("option").nth(2)
    second_group_id = second_group.get_attribute("value")
    second_user_type_id = second_user_type.get_attribute("value")
    second_group_name = second_group.inner_text()
    second_user_type_name = second_user_type.inner_text()
    assert second_group_id
    assert second_user_type_id

    edit_modal.locator('input[name="username"]').fill(updated_name)
    edit_group_select.select_option(value=second_group_id)
    edit_user_type_select.select_option(value=second_user_type_id)
    edit_modal.get_by_role("button", name="更新").click()

    expect(edit_modal).to_be_hidden()
    updated_row = page.locator(f"#user-row-{user_id}")
    expect(updated_row).to_contain_text(updated_name)
    expect(updated_row).to_contain_text(second_group_name)
    expect(updated_row).to_contain_text(second_user_type_name)
    expect(updated_row).not_to_contain_text(initial_name)

    updated_row.get_by_role("button", name="削除").click()
    delete_modal = page.locator(f"#user-delete-modal-{user_id}")
    expect(delete_modal).to_be_visible()
    delete_modal.get_by_role("button", name="削除").click()

    expect(delete_modal).to_be_hidden()
    expect(page.locator(f"#user-row-{user_id}")).not_to_be_visible()
