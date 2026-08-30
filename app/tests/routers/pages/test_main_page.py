import pytest
from httpx import AsyncClient
from fastapi import status

@pytest.mark.asyncio
async def test_read_main(async_client: AsyncClient) -> None:
    """ルートパスへのGETリクエストが成功することを確認する"""
    response = await async_client.get("/")
    assert response.status_code == status.HTTP_200_OK
    # 必要に応じて、レスポンスの内容も検証できます
    # assert "<h1>Sokora</h1>" in response.text 