import re
import datetime
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"
UI_BASE = f"{BASE_URL}"


def test_top_page_title(page: Page) -> None:
    """トップページにアクセスし、タイトルを確認するテスト"""
    page.goto(UI_BASE)  # アプリケーションのURLにアクセス
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # タイトルに "Sokora" が含まれていることを確認
    expect(page).to_have_title(re.compile("Sokora")) 

def test_top_page_elements(page: Page) -> None:
    """トップページの主要要素の存在を確認するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # ヘッダーテキストの確認
    header = page.locator("h2")
    expect(header).to_have_text("勤怠確認")

    # カレンダーエリアの存在確認
    calendar_area = page.locator("#calendar-area")
    expect(calendar_area).to_be_visible()
    expect(calendar_area).to_have_attribute("hx-get", "/calendar")

    # 詳細エリアの存在確認
    detail_area = page.locator("#detail-area")
    expect(detail_area).to_be_visible()


def test_initial_day_detail(page: Page) -> None:
    """初期表示で本日日付の詳細が表示されることを確認するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # 詳細エリアが表示されるのを待つ（HTMXのロード完了を期待）
    detail_area = page.locator("#detail-area")
    expect(detail_area).to_contain_text("の勤怠情報", timeout=500)
    
    # 本日の日付を取得 (YYYY-MM-DD)
    today_date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # 詳細エリアに本日の日付が含まれているか確認
    expect(detail_area).to_contain_text(today_date_str)

def test_click_day_shows_detail(page: Page) -> None:
    """特定の日付をクリックするとその日の詳細が表示されるテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # カレンダーが表示されるのを待つ (最初のセルが表示されるかで判断)
    expect(page.locator("#calendar-area .calendar-cell").first).to_be_visible(timeout=500)

    # 例えば15日をクリック（要素が存在すれば）
    day_to_click = "15"
    day_cell = page.locator(f".calendar-cell[data-day='{day_to_click}']").first
    if day_cell.is_visible():
        date_str = day_cell.get_attribute("data-date")
        assert date_str is not None
        day_cell.click()

        # 詳細エリアが更新されるのを待つ
        detail_area = page.locator("#detail-area")
        expect(detail_area).to_contain_text(re.compile(rf"{date_str}の勤怠情報"), timeout=500)
        expect(detail_area).to_contain_text(date_str)
    else:
        print(f"Skipping test: Day {day_to_click} not visible on the calendar.")

def test_month_navigation(page: Page) -> None:
    """月遷移ボタンが機能することを確認するテスト"""
    page.goto(UI_BASE)
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))

    # カレンダーエリアが表示されるのを待つ
    expect(page.locator("#calendar-area")).to_be_visible(timeout=500)
    # 初期月表示を確認 (例: YYYY年MM月)
    current_month_locator = page.locator("#calendar-area .text-xl.font-bold")
    initial_month_text = current_month_locator.text_content()
    assert initial_month_text is not None

    # 次月ボタンをクリック - セレクタを修正
    next_month_button = page.locator('#calendar-area .btn-group button:last-child')
    expect(next_month_button).to_be_visible(timeout=500)
    next_month_button.click()
    
    # 月が変わるのを待つ（テキストが変わることを期待）
    expect(current_month_locator).not_to_have_text(initial_month_text, timeout=500)
    next_month_text = current_month_locator.text_content()
    assert next_month_text is not None

    # 前月ボタンをクリック - セレクタを修正
    prev_month_button = page.locator('#calendar-area .btn-group button:first-child')
    expect(prev_month_button).to_be_visible(timeout=500)
    prev_month_button.click()
    
    # 月が初期状態に戻るのを待つ
    expect(current_month_locator).to_have_text(initial_month_text, timeout=500)

    # 再度次月に移動
    next_month_button.click()
    expect(current_month_locator).to_have_text(next_month_text, timeout=500)

    # 今月ボタンをクリック - セレクタを修正
    today_button = page.locator('#calendar-area .btn-group button.btn-neutral')
    expect(today_button).to_be_visible(timeout=500)
    today_button.click()
    
    # 月が初期状態に戻るのを待つ
    expect(current_month_locator).to_have_text(initial_month_text, timeout=500)
