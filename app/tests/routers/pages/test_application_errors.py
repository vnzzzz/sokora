from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app import crud
from app.schemas.group import GroupCreate
from app.services.errors import DataIntegrityError


@pytest.mark.asyncio
async def test_group_page_delete_renders_integrity_error_in_html(
    async_client: AsyncClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Page writeではDB競合エラーをJSON化せず既存modalへ表示する。"""
    created = crud.group.create(db, obj_in=GroupCreate(name="page-error-group"))
    db.commit()
    group_id = int(created.id)

    def fail_delete(*_args, **_kwargs):
        raise DataIntegrityError("利用中のグループは削除できません")

    monkeypatch.setattr(
        "app.routers.pages.group.group_service.delete_group",
        fail_delete,
    )

    response = await async_client.delete(f"/groups/{group_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "利用中のグループは削除できません" in response.text
    assert crud.group.get(db, id=group_id) is not None


@pytest.mark.asyncio
async def test_holiday_page_create_renders_integrity_error_in_html(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent holiday重複もpage modalのfield errorとして表示する。"""

    def fail_create(*_args, **_kwargs):
        raise DataIntegrityError("この日付は既に登録されています")

    monkeypatch.setattr(
        "app.routers.pages.holiday.custom_holiday_service.create_custom_holiday_with_validation",
        fail_create,
    )

    response = await async_client.post(
        "/holidays",
        data={"date": date(2030, 1, 1).isoformat(), "name": "Concurrent Holiday"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "この日付は既に登録されています" in response.text
