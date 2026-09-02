from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.settings import AppSettings
from app.db.session import create_database_runtime, initialize_database
from app.main import create_application


def _sqlite_admin_app(tmp_path: Path):
    database_path = tmp_path / "sokora.db"
    settings = AppSettings(
        database_url=f"sqlite:///{database_path}",
        auth_enabled=True,
        session_secret="database-management-test-secret",
        local_auth_enabled=True,
        local_admin_username="admin",
        local_admin_password="secret",
    )
    application = create_application(settings)
    runtime = create_database_runtime(settings.database_url)
    initialize_database(runtime)
    application.state.database_runtime = runtime
    return application, runtime


async def _login_admin(client: AsyncClient, next_path: str = "/admin/database") -> None:
    response = await client.post(
        "/auth/local",
        data={
            "username": "admin",
            "password": "secret",
            "next": next_path,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


@pytest.mark.asyncio
async def test_database_management_is_admin_only(tmp_path: Path) -> None:
    application, runtime = _sqlite_admin_app(tmp_path)
    transport = ASGITransport(app=application)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            unauthenticated = await client.get(
                "/admin/database",
                follow_redirects=False,
            )
            assert unauthenticated.status_code == 307
            assert unauthenticated.headers["location"].startswith("/auth/login")

            await _login_admin(client)
            page = await client.get("/admin/database")
            assert page.status_code == 200
            assert "データベース管理" in page.text
            assert "バックアップをダウンロード" in page.text
            assert "検証してリストア" in page.text
    finally:
        runtime.dispose()


@pytest.mark.asyncio
async def test_database_backup_and_restore_round_trip(tmp_path: Path) -> None:
    application, runtime = _sqlite_admin_app(tmp_path)
    transport = ASGITransport(app=application)

    try:
        with runtime.session_factory() as db:
            row = db.execute(
                text("select id, name from groups order by id limit 1")
            ).one()
            group_id = int(row.id)
            original_name = str(row.name)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _login_admin(client)

            backup = await client.get("/admin/database/backup")
            assert backup.status_code == 200
            assert backup.content.startswith(b"SQLite format 3\x00")
            assert "attachment;" in backup.headers["content-disposition"]

            with runtime.session_factory() as db:
                db.execute(
                    text("update groups set name = :name where id = :group_id"),
                    {"name": "changed-after-download", "group_id": group_id},
                )
                db.commit()

            restore = await client.post(
                "/admin/database/restore",
                data={"confirm_restore": "yes"},
                files={
                    "database": (
                        "backup.db",
                        backup.content,
                        "application/vnd.sqlite3",
                    )
                },
                follow_redirects=False,
            )
            assert restore.status_code == 303
            assert restore.headers["location"] == "/admin/database?result=restored"

            completed = await client.get(restore.headers["location"])
            assert completed.status_code == 200
            assert "DB接続を再初期化しました" in completed.text

        with runtime.session_factory() as db:
            restored_name = db.scalar(
                text("select name from groups where id = :group_id"),
                {"group_id": group_id},
            )
        assert restored_name == original_name
    finally:
        runtime.dispose()


@pytest.mark.asyncio
async def test_restore_rejects_invalid_database(tmp_path: Path) -> None:
    application, runtime = _sqlite_admin_app(tmp_path)
    transport = ASGITransport(app=application)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _login_admin(client)

            response = await client.post(
                "/admin/database/restore",
                data={"confirm_restore": "yes"},
                files={
                    "database": (
                        "invalid.db",
                        b"not a database",
                        "application/octet-stream",
                    )
                },
            )
            assert response.status_code == 400
            assert "SQLiteデータベースではない" in response.text
    finally:
        runtime.dispose()


@pytest.mark.asyncio
async def test_postgresql_backend_disables_database_file_operations() -> None:
    settings = AppSettings(
        database_url="postgresql://user:password@db.example:5432/sokora",
        auth_enabled=True,
        session_secret="database-management-test-secret",
        local_auth_enabled=True,
        local_admin_username="admin",
        local_admin_password="secret",
    )
    application = create_application(settings)
    transport = ASGITransport(app=application)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _login_admin(client)
        page = await client.get("/admin/database")

    runtime = application.state.database_runtime
    try:
        assert page.status_code == 200
        assert "GUI管理" in page.text
        assert "無効" in page.text
        assert "backup/restore機能はファイルベースSQLite専用" in page.text
        assert "/admin/database/restore" not in page.text
    finally:
        runtime.dispose()
