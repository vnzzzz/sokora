from pathlib import Path

from playwright.sync_api import Page, expect

CSV_URL = "http://localhost:8000/csv"


def test_csv_page_download_button_starts_real_download(page: Page) -> None:
    page.goto(CSV_URL)
    expect(page).to_have_title("Sokora - CSVダウンロード")
    expect(page.locator("#month-select")).to_be_visible()
    expect(page.locator("#encoding-utf8")).to_be_checked()

    with page.expect_download(timeout=5000) as download_info:
        page.locator("#download-btn").click()

    download = download_info.value
    assert download.suggested_filename.endswith(".csv")
    downloaded_path = download.path()
    assert downloaded_path is not None
    assert Path(downloaded_path).is_file()
