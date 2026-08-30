"""
トップページのテストケース
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from starlette.responses import HTMLResponse

from app.main import app


class TestTopPage:
    """トップページのテスト"""

    def setup_method(self) -> None:
        """テスト用のセットアップ"""
        self.client = TestClient(app)

    def test_read_root_success(self) -> None:
        """トップページの正常表示テスト"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        
        # HTMLコンテンツの基本的な確認
        content = response.text
        assert "Sokora" in content
        assert "勤怠管理" in content

    @patch('app.routers.pages.top.logger')
    def test_read_root_logging(self, mock_logger: MagicMock) -> None:
        """トップページアクセス時のログ出力テスト"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        mock_logger.info.assert_called_once_with("Top page accessed")

    @patch('app.routers.pages.top.templates')
    def test_read_root_template_response(self, mock_templates: MagicMock) -> None:
        """テンプレートレスポンスの確認"""
        # HTMLResponseを返すようにモック設定
        mock_response = HTMLResponse("<html><body>Test</body></html>")
        mock_templates.TemplateResponse.return_value = mock_response
        
        response = self.client.get("/")
        
        assert response.status_code == 200
        
        # テンプレートが正しい引数で呼ばれることを確認
        mock_templates.TemplateResponse.assert_called_once()
        call_args = mock_templates.TemplateResponse.call_args
        
        assert call_args[0][0] == "pages/top.html"  # テンプレートファイル名
        context = call_args[0][1]
        assert "request" in context
        assert context["title_text"] == "Sokora - 勤怠管理" 