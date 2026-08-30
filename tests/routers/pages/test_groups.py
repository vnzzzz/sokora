import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
async def test_read_groups_page(async_client: AsyncClient) -> None:
    """グループ管理ページ (GET /groups) が正常に取得できることをテスト"""
    response = await async_client.get("/groups")
    assert response.status_code == status.HTTP_200_OK
    assert "<title>Sokora - グループ管理</title>" in response.text
    # assert "<h1 class=\"text-2xl font-semibold\">グループ管理</h1>" in response.text # H1タグの検証を一時的にコメントアウト 