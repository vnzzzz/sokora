import datetime

from app.models.custom_holiday import CustomHoliday


async def test_get_holidays_page(async_client, db) -> None:
    """祝日管理ページが表示され、登録済みの祝日が見える"""
    db.add(CustomHoliday(date=datetime.date(2024, 12, 31), name="テスト休"))
    db.commit()

    response = await async_client.get("/holidays")

    assert response.status_code == 200
    assert "祝日管理" in response.text
    assert "テスト休" in response.text
    assert "ビルド時の祝日" not in response.text
    assert "max-w-[700px]" in response.text
    assert "table-responsive" in response.text


async def test_create_holiday_from_ui(async_client, db) -> None:
    """フォーム経由で祝日を追加できる"""
    response = await async_client.post(
        "/holidays",
        data={"date": "2024-12-30", "name": "UI追加"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert db.query(CustomHoliday).count() == 1


async def test_holidays_page_shows_empty_state(async_client, db) -> None:
    """祝日が無い場合は共通デザインの空表示を出す"""
    response = await async_client.get("/holidays")

    assert response.status_code == 200
    assert "alert alert-info" in response.text
    assert "カスタム祝日は登録されていません" in response.text
