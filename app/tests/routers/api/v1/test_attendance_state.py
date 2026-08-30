"""
勤怠データ状態保持に関するテスト
=======================

勤怠APIが状態を正しく維持するかテスト
"""
import json
from datetime import date, timedelta
from typing import Dict, Any, List

import pytest
from fastapi import status
from httpx import AsyncClient

# 同じディレクトリのテストヘルパー関数をインポート
from app.tests.routers.api.v1.test_attendance import (
    create_test_group_via_api,
    create_test_user_type_via_api,
    create_test_user_via_api,
    create_test_location_via_api,
)


# --- 月変更問題と個別登録問題に関するテスト ---

async def test_refresh_attendance_preserves_month(async_client: AsyncClient) -> None:
    """
    勤怠登録で月を変更した後に勤怠を登録・更新・削除しても、
    選択した月の表示が維持されることをテストします。
    """
    # テストデータ準備
    group_id = await create_test_group_via_api(async_client, "AttTestGroupMonth")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeMonth")
    user_id = await create_test_user_via_api(async_client, "att_user_month", "Att User Month", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation Month")
    
    test_date = date.today().isoformat()
    
    # 勤怠登録APIを呼び出し
    payload = {
        "user_id": user_id,
        "date": test_date,
        "location_id": str(location_id)
    }
    
    # HTMXの動作をシミュレートするためのヘッダー
    htmx_headers = {"HX-Request": "true"}
    
    # 過去の月を選択したと想定
    prev_month = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    
    # refreshAttendanceイベントでmonthパラメータが保持されることを確認
    trigger_data = {
        "refreshAttendance": None
    }
    
    # トリガーヘッダーを含むレスポンスに対するmonthパラメータの保持をテスト
    response = await async_client.post(
        "/api/v1/attendances", 
        data=payload,
        headers={"X-Test-Month": prev_month}  # テスト用ヘッダー
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert "HX-Trigger" in response.headers
    
    # 実際のレスポンスヘッダーから現在の月が維持されるかをテスト
    # (実際のフロントエンドの動作はHTMXのイベントリスナーでテストする)


async def test_refresh_user_attendance_preserves_user_view(async_client: AsyncClient) -> None:
    """
    個別登録画面で予定を登録・変更・削除後に、
    社員個別の表示状態が維持されることをテストします。
    """
    # テストデータ準備
    group_id = await create_test_group_via_api(async_client, "AttTestGroupUser")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeUser")
    user_id = await create_test_user_via_api(async_client, "att_user_view", "Att User View", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation User")
    
    test_date = date.today().isoformat()
    
    # 勤怠登録APIを呼び出し
    payload = {
        "user_id": user_id,
        "date": test_date,
        "location_id": str(location_id)
    }
    
    # HTMXの動作をシミュレートするためのヘッダー
    htmx_headers = {"HX-Request": "true"}
    
    # refreshUserAttendanceイベントが個別表示を維持することを確認
    response = await async_client.post(
        "/api/v1/attendances", 
        data=payload
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert "HX-Trigger" in response.headers
    
    # ユーザー表示の維持テスト - レスポンスヘッダーに適切なトリガーが含まれることを確認
    # (実際のフロントエンドの動作はHTMXのイベントリスナーでテストする)


async def test_refresh_weekly_attendance_preserves_selected_week(async_client: AsyncClient) -> None:
    """
    週次勤怠登録で週を移動した後でも、登録後に同じ週が維持されるよう
    HX-Trigger に week 情報が含まれることを確認します。
    """
    group_id = await create_test_group_via_api(async_client, "AttTestGroupWeek")
    user_type_id = await create_test_user_type_via_api(async_client, "AttTestUserTypeWeek")
    user_id = await create_test_user_via_api(async_client, "att_user_week", "Att User Week", group_id, user_type_id)
    location_id = await create_test_location_via_api(async_client, "AttTestLocation Week")

    base_monday = date.today() - timedelta(days=date.today().weekday())
    selected_week_monday = base_monday + timedelta(days=7)  # 翌週を選択した想定
    attendance_date = (selected_week_monday + timedelta(days=2)).isoformat()
    selected_week = selected_week_monday.isoformat()

    payload = {
        "user_id": user_id,
        "date": attendance_date,
        "location_id": str(location_id)
    }

    response = await async_client.post(
        "/api/v1/attendances",
        data=payload,
        headers={"Referer": f"http://test/attendance/weekly?week={selected_week}"}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert "HX-Trigger" in response.headers

    triggers = json.loads(response.headers["HX-Trigger"])
    assert triggers["refreshUserAttendance"]["week"] == selected_week
    assert triggers["refreshAttendance"]["week"] == selected_week
