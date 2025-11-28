"""
CSVページのテストケース
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from starlette.responses import HTMLResponse

from app.main import app


class TestCsvPage:
    """CSVページのテスト"""

    def setup_method(self) -> None:
        """テスト用のセットアップ"""
        self.client = TestClient(app)

    @patch('app.routers.pages.csv.get_available_months')
    def test_csv_page_success(self, mock_get_months: MagicMock) -> None:
        """CSVページの正常表示テスト"""
        # モックデータ
        mock_months = [
            {"value": "2024-01", "label": "2024年1月"},
            {"value": "2024-02", "label": "2024年2月"}
        ]
        mock_get_months.return_value = mock_months
        
        response = self.client.get("/ui/csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        
        # get_available_monthsが呼ばれることを確認
        mock_get_months.assert_called_once()

    @patch('app.routers.pages.csv.templates')
    @patch('app.routers.pages.csv.get_available_months')
    def test_csv_page_template_response(self, mock_get_months: MagicMock, mock_templates: MagicMock) -> None:
        """テンプレートレスポンスの確認"""
        # モックデータ
        mock_months = [
            {"value": "2024-01", "label": "2024年1月"},
            {"value": "2024-02", "label": "2024年2月"}
        ]
        mock_get_months.return_value = mock_months
        
        # HTMLResponseを返すようにモック設定
        mock_response = HTMLResponse("<html><body>CSV Page</body></html>")
        mock_templates.TemplateResponse.return_value = mock_response
        
        response = self.client.get("/ui/csv")
        
        assert response.status_code == 200
        
        # テンプレートが正しい引数で呼ばれることを確認
        mock_templates.TemplateResponse.assert_called_once()
        call_args = mock_templates.TemplateResponse.call_args
        
        assert call_args[0][0] == "pages/csv.html"  # テンプレートファイル名
        context = call_args[0][1]
        assert "request" in context
        assert context["months"] == mock_months

    @patch('app.routers.pages.csv.get_available_months')
    def test_csv_page_with_empty_months(self, mock_get_months: MagicMock) -> None:
        """月データが空の場合のテスト"""
        mock_get_months.return_value = []
        
        response = self.client.get("/ui/csv")
        
        assert response.status_code == 200
        mock_get_months.assert_called_once()

    @patch('app.routers.pages.csv.get_available_months')
    def test_csv_page_with_exception(self, mock_get_months: MagicMock) -> None:
        """get_available_monthsで例外が発生した場合のテスト"""
        mock_get_months.side_effect = Exception("Database error")
        
        # 例外が発生してもページは表示される（エラーハンドリングによる）
        with pytest.raises(Exception):
            self.client.get("/ui/csv")
