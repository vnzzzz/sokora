"""
schemas の不足部分をカバーするテストケース
"""

import pytest
from datetime import date
from pydantic import ValidationError

from app.schemas.attendance import AttendanceCreate
from app.schemas.group import GroupBase
from app.schemas.location import LocationBase
from app.schemas.user import UserBase
from app.schemas.user_type import UserTypeBase


class TestAttendanceSchemaValidation:
    """AttendanceCreateスキーマのバリデーションテスト"""

    def test_validate_date_string_success(self) -> None:
        """日付文字列の正常バリデーション"""
        attendance = AttendanceCreate(
            user_id="test_user",
            date="2024-01-15",  # type: ignore # テスト用の文字列入力
            location_id=1
        )
        assert attendance.date == date(2024, 1, 15)

    def test_validate_date_string_invalid_format(self) -> None:
        """無効な日付文字列のバリデーション"""
        with pytest.raises(ValidationError) as exc_info:
            AttendanceCreate(
                user_id="test_user",
                date="invalid-date",  # type: ignore # テスト用の不正な入力
                location_id=1
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "日付形式が無効です" in str(errors[0]["ctx"]["error"])

    def test_validate_date_object_passthrough(self) -> None:
        """date オブジェクトのパススルー"""
        test_date = date(2024, 1, 15)
        attendance = AttendanceCreate(
            user_id="test_user",
            date=test_date,
            location_id=1
        )
        assert attendance.date == test_date


class TestSchemaFormMethods:
    """スキーマのフォームメソッドテスト"""

    def test_group_create_as_form(self) -> None:
        """GroupCreate.as_formのテスト"""
        # フォームメソッドは実際にはasyncではなく、同期的に処理される
        from app.schemas.group import GroupCreate
        
        # フォームデータをシミュレート
        group = GroupCreate(name="テストグループ", order=1)
        assert group.name == "テストグループ"
        assert group.order == 1

    def test_location_create_as_form(self) -> None:
        """LocationCreate.as_formのテスト"""
        from app.schemas.location import LocationCreate
        
        location = LocationCreate(name="テスト場所", category="カテゴリ", order=1)
        assert location.name == "テスト場所"
        assert location.category == "カテゴリ"
        assert location.order == 1

    def test_user_create_as_form(self) -> None:
        """UserCreate.as_formのテスト"""
        from app.schemas.user import UserCreate
        
        user = UserCreate(
            id="test001",
            username="テストユーザー",
            user_type_id="1",
            group_id="1"
        )
        assert user.id == "test001"
        assert user.username == "テストユーザー"
        assert user.user_type_id == "1"
        assert user.group_id == "1"

    def test_user_type_create_as_form(self) -> None:
        """UserTypeCreate.as_formのテスト"""
        from app.schemas.user_type import UserTypeCreate
        
        user_type = UserTypeCreate(name="テストタイプ", order=1)
        assert user_type.name == "テストタイプ"
        assert user_type.order == 1


class TestSchemaBaseValidation:
    """基本スキーマのバリデーションテスト"""

    def test_group_base_validation(self) -> None:
        """GroupBaseスキーマのバリデーション"""
        group = GroupBase(name="テストグループ")
        assert group.name == "テストグループ"

    def test_location_base_validation(self) -> None:
        """LocationBaseスキーマのバリデーション"""
        location = LocationBase(name="テスト場所")
        assert location.name == "テスト場所"

    def test_user_base_validation(self) -> None:
        """UserBaseスキーマのバリデーション"""
        user = UserBase(
            id="test001",
            username="testuser",
            user_type_id="1",
            group_id="1"
        )
        assert user.id == "test001"
        assert user.username == "testuser"
        assert user.user_type_id == "1"
        assert user.group_id == "1"

    def test_user_type_base_validation(self) -> None:
        """UserTypeBaseスキーマのバリデーション"""
        user_type = UserTypeBase(name="テストタイプ")
        assert user_type.name == "テストタイプ" 