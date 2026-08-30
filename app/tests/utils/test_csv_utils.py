"""
csv_utils のテストケース
"""

import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from typing import Any

from app.utils.csv_utils import (
    get_available_months, get_date_range_for_month, _generate_date_headers,
    generate_work_entries_csv_rows
)


class TestGetAvailableMonths:
    """get_available_months関数のテスト"""

    @patch('app.utils.csv_utils.datetime')
    def test_get_available_months_default(self, mock_datetime: Any) -> None:
        """get_available_months関数のテスト（デフォルト）"""
        mock_datetime.now.return_value.date.return_value = datetime.date(2024, 3, 15)
        
        result = get_available_months(3)
        
        assert len(result) == 3
        assert result[0]["value"] == "2024-03"
        assert result[0]["label"] == "2024年3月"
        assert result[1]["value"] == "2024-02"
        assert result[1]["label"] == "2024年2月"
        assert result[2]["value"] == "2024-01"
        assert result[2]["label"] == "2024年1月"

    @patch('app.utils.csv_utils.datetime')
    def test_get_available_months_cross_year(self, mock_datetime: Any) -> None:
        """get_available_months関数のテスト（年跨ぎ）"""
        mock_datetime.now.return_value.date.return_value = datetime.date(2024, 1, 15)
        
        result = get_available_months(3)
        
        assert len(result) == 3
        assert result[0]["value"] == "2024-01"
        assert result[0]["label"] == "2024年1月"
        assert result[1]["value"] == "2023-12"
        assert result[1]["label"] == "2023年12月"
        assert result[2]["value"] == "2023-11"
        assert result[2]["label"] == "2023年11月"

    @patch('app.utils.csv_utils.datetime')
    def test_get_available_months_single(self, mock_datetime: Any) -> None:
        """get_available_months関数のテスト（1ヶ月）"""
        mock_datetime.now.return_value.date.return_value = datetime.date(2024, 6, 15)
        
        result = get_available_months(1)
        
        assert len(result) == 1
        assert result[0]["value"] == "2024-06"
        assert result[0]["label"] == "2024年6月"


class TestGetDateRangeForMonth:
    """get_date_range_for_month関数のテスト"""

    def test_get_date_range_for_month_normal(self) -> None:
        """get_date_range_for_month関数のテスト（通常月）"""
        start_date, end_date = get_date_range_for_month("2024-03")
        
        assert start_date == datetime.date(2024, 3, 1)
        assert end_date == datetime.date(2024, 3, 31)

    def test_get_date_range_for_month_february_leap(self) -> None:
        """get_date_range_for_month関数のテスト（うるう年2月）"""
        start_date, end_date = get_date_range_for_month("2024-02")
        
        assert start_date == datetime.date(2024, 2, 1)
        assert end_date == datetime.date(2024, 2, 29)

    def test_get_date_range_for_month_february_normal(self) -> None:
        """get_date_range_for_month関数のテスト（平年2月）"""
        start_date, end_date = get_date_range_for_month("2023-02")
        
        assert start_date == datetime.date(2023, 2, 1)
        assert end_date == datetime.date(2023, 2, 28)

    def test_get_date_range_for_month_january(self) -> None:
        """get_date_range_for_month関数のテスト（1月）"""
        start_date, end_date = get_date_range_for_month("2024-01")
        
        assert start_date == datetime.date(2024, 1, 1)
        assert end_date == datetime.date(2024, 1, 31)

    def test_get_date_range_for_month_december(self) -> None:
        """get_date_range_for_month関数のテスト（12月）"""
        start_date, end_date = get_date_range_for_month("2024-12")
        
        assert start_date == datetime.date(2024, 12, 1)
        assert end_date == datetime.date(2024, 12, 31)


class TestGenerateDateHeaders:
    """_generate_date_headers関数のテスト"""

    def test_generate_date_headers_with_month(self) -> None:
        """_generate_date_headers関数のテスト（月指定あり）"""
        result = _generate_date_headers("2024-02")
        
        assert len(result) == 29  # 2024年2月はうるう年
        assert result[0] == "2024/02/01"
        assert result[-1] == "2024/02/29"

    def test_generate_date_headers_with_month_january(self) -> None:
        """_generate_date_headers関数のテスト（1月）"""
        result = _generate_date_headers("2024-01")
        
        assert len(result) == 31
        assert result[0] == "2024/01/01"
        assert result[-1] == "2024/01/31"

    @patch('app.utils.csv_utils.date')
    def test_generate_date_headers_without_month(self, mock_date: Any) -> None:
        """_generate_date_headers関数のテスト（月指定なし）"""
        mock_date.today.return_value = datetime.date(2024, 3, 15)
        
        result = _generate_date_headers()
        
        assert len(result) == 90  # デフォルトの90日
        # ソートされているかを確認
        assert result[0] < result[-1]
        # 日付形式を確認
        assert result[0].count('/') == 2
        assert len(result[0]) == 10  # YYYY/MM/DD


class TestGenerateWorkEntriesCsvRows:
    """generate_work_entries_csv_rows関数のテスト"""

    def setup_method(self) -> None:
        """テスト用のセットアップ"""
        self.mock_db = MagicMock(spec=Session)

    @patch('app.utils.csv_utils.crud_user')
    @patch('app.utils.csv_utils.crud_attendance')
    def test_generate_work_entries_csv_rows_with_data(self, mock_crud_attendance: Any, mock_crud_user: Any) -> None:
        """generate_work_entries_csv_rows関数のテスト（データあり）"""
        # モックデータの準備
        mock_crud_user.get_all_users_with_details.return_value = [
            ("田中太郎", "user001", "営業部", "正社員"),
            ("佐藤花子", "user002", "開発部", "契約社員")
        ]
        
        mock_crud_attendance.get_attendance_data_for_csv.return_value = {
            "user001_2024-02-01": "オフィス",
            "user001_2024-02-02": "リモート",
            "user002_2024-02-01": "リモート",
            "user002_2024-02-02": ""
        }
        
        # ジェネレータからリストに変換
        rows = list(generate_work_entries_csv_rows(self.mock_db, "2024-02"))
        
        # ヘッダー行
        assert rows[0][0] == "user_name"
        assert rows[0][1] == "user_id"
        assert rows[0][2] == "group_name"
        assert rows[0][3] == "user_type"
        assert rows[0][4] == "2024/02/01"
        assert rows[0][5] == "2024/02/02"
        
        # データ行1（田中太郎）
        assert rows[1][0] == "田中太郎"
        assert rows[1][1] == "user001"
        assert rows[1][2] == "営業部"
        assert rows[1][3] == "正社員"
        assert rows[1][4] == "オフィス"  # 2024/02/01
        assert rows[1][5] == "リモート"  # 2024/02/02
        
        # データ行2（佐藤花子）
        assert rows[2][0] == "佐藤花子"
        assert rows[2][1] == "user002"
        assert rows[2][2] == "開発部"
        assert rows[2][3] == "契約社員"
        assert rows[2][4] == "リモート"  # 2024/02/01
        assert rows[2][5] == ""  # 2024/02/02

    @patch('app.utils.csv_utils.crud_user')
    @patch('app.utils.csv_utils.crud_attendance')
    def test_generate_work_entries_csv_rows_no_users(self, mock_crud_attendance: Any, mock_crud_user: Any) -> None:
        """generate_work_entries_csv_rows関数のテスト（ユーザーなし）"""
        mock_crud_user.get_all_users_with_details.return_value = []
        
        rows = list(generate_work_entries_csv_rows(self.mock_db, "2024-02"))
        
        # ヘッダー行のみ
        assert len(rows) == 1
        assert rows[0][0] == "user_name"

    @patch('app.utils.csv_utils.crud_user')
    @patch('app.utils.csv_utils.crud_attendance')
    def test_generate_work_entries_csv_rows_no_month(self, mock_crud_attendance: Any, mock_crud_user: Any) -> None:
        """generate_work_entries_csv_rows関数のテスト（月指定なし）"""
        mock_crud_user.get_all_users_with_details.return_value = [
            ("テストユーザー", "test001", "テスト部", "テスト")
        ]
        mock_crud_attendance.get_attendance_data_for_csv.return_value = {}
        
        with patch('app.utils.csv_utils.date') as mock_date:
            mock_date.today.return_value = datetime.date(2024, 3, 15)
            
            rows = list(generate_work_entries_csv_rows(self.mock_db))
            
            # ヘッダー行 + データ行
            assert len(rows) == 2
            # ヘッダーには90日分のデータがある
            assert len(rows[0]) == 4 + 90  # user_info(4) + dates(90)

    @patch('app.utils.csv_utils.crud_user')
    def test_generate_work_entries_csv_rows_error_handling(self, mock_crud_user: Any) -> None:
        """generate_work_entries_csv_rows関数のテスト（エラー処理）"""
        # ユーザー取得でエラーを発生
        mock_crud_user.get_all_users_with_details.side_effect = Exception("DB Error")
        
        rows = list(generate_work_entries_csv_rows(self.mock_db, "2024-02"))
        
        # ヘッダー行 + エラー行
        assert len(rows) == 2
        assert rows[0][0] == "user_name"  # ヘッダー行
        assert rows[1][0] == "Error generating CSV data"  # エラー行

    @patch('app.utils.csv_utils.crud_user')
    @patch('app.utils.csv_utils.crud_attendance')
    def test_generate_work_entries_csv_rows_none_values(self, mock_crud_attendance: Any, mock_crud_user: Any) -> None:
        """generate_work_entries_csv_rows関数のテスト（None値処理）"""
        # None値を含むデータ
        mock_crud_user.get_all_users_with_details.return_value = [
            (None, None, None, None),
            ("田中太郎", "user001", None, "正社員")
        ]
        mock_crud_attendance.get_attendance_data_for_csv.return_value = {}
        
        rows = list(generate_work_entries_csv_rows(self.mock_db, "2024-01"))
        
        # None値は空文字に変換される
        assert rows[1][0] == ""  # user_name
        assert rows[1][1] == ""  # user_id
        assert rows[1][2] == ""  # group_name
        assert rows[1][3] == ""  # user_type
        
        assert rows[2][0] == "田中太郎"
        assert rows[2][1] == "user001"
        assert rows[2][2] == ""  # None → ""
        assert rows[2][3] == "正社員" 