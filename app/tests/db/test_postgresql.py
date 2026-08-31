"""PostgreSQL backend contract tests.

The integration test is skipped unless ``SOKORA_TEST_POSTGRES_URL`` points to a
real PostgreSQL instance. CI provides that database through a service container.
"""

import os
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.core.settings import AppSettings
from app.db.session import (
    _database_url_for_logging,
    create_database_runtime,
    sqlalchemy_database_url,
)
from app.main import create_application


def test_bare_postgresql_url_uses_psycopg3() -> None:
    url = sqlalchemy_database_url(
        "postgresql://sokora:secret@db.example:5432/sokora?sslmode=require"
    )

    assert url.drivername == "postgresql+psycopg"
    assert url.host == "db.example"
    assert url.database == "sokora"
    assert url.query["sslmode"] == "require"


def test_explicit_postgresql_driver_is_preserved() -> None:
    url = sqlalchemy_database_url("postgresql+pg8000://sokora@db.example/sokora")

    assert url.drivername == "postgresql+pg8000"


def test_database_url_logging_omits_credentials_and_query_parameters() -> None:
    database_url = (
        "postgresql://sokora:s3cr%40t@db.example:5432/sokora"
        "?sslmode=require&sslpassword=tls-secret&application_name=sokora"
    )
    runtime = create_database_runtime(database_url)
    try:
        diagnostic_url = _database_url_for_logging(runtime.database_url)

        assert runtime.database_url == database_url
        assert runtime.engine.url.password == "s3cr@t"
        assert runtime.engine.url.drivername == "postgresql+psycopg"
        assert runtime.engine.url.query["sslmode"] == "require"
        assert runtime.engine.url.query["sslpassword"] == "tls-secret"
        assert runtime.engine.url.query["application_name"] == "sokora"

        assert "s3cr@t" not in diagnostic_url
        assert "s3cr%40t" not in diagnostic_url
        assert "tls-secret" not in diagnostic_url
        assert "sslpassword" not in diagnostic_url
        assert "sslmode" not in diagnostic_url
        assert "application_name" not in diagnostic_url
        assert ":***@" in diagnostic_url
        assert "?" not in diagnostic_url
    finally:
        runtime.dispose()


def test_postgresql_startup_migration_and_major_crud() -> None:
    database_url = os.getenv("SOKORA_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("SOKORA_TEST_POSTGRES_URL is not configured")

    settings = AppSettings(database_url=database_url, auth_enabled=False)
    app = create_application(settings)
    suffix = uuid4().hex[:10]

    with TestClient(app) as client:
        runtime = app.state.database_runtime
        assert runtime.engine.url.drivername == "postgresql+psycopg"

        tables = set(inspect(runtime.engine).get_table_names())
        assert {
            "alembic_version",
            "groups",
            "user_types",
            "locations",
            "users",
            "attendance",
            "custom_holidays",
        } <= tables
        with runtime.session_factory() as db:
            assert db.scalar(text("select version_num from alembic_version"))

        assert client.get("/healthz").status_code == 200

        # Master CRUD: create -> read/list -> update -> delete.
        group_response = client.post(
            "/api/v1/groups", json={"name": f"pg-crud-{suffix}"}
        )
        assert group_response.status_code == 200
        disposable_group_id = group_response.json()["id"]

        updated_group_name = f"pg-crud-updated-{suffix}"
        update_response = client.put(
            f"/api/v1/groups/{disposable_group_id}",
            json={"name": updated_group_name},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == updated_group_name

        list_response = client.get("/api/v1/groups")
        assert list_response.status_code == 200
        assert updated_group_name in {
            group["name"] for group in list_response.json()["groups"]
        }

        delete_response = client.delete(f"/api/v1/groups/{disposable_group_id}")
        assert delete_response.status_code == 204

        # Relational/domain CRUD path used by attendance.
        group_id = client.post(
            "/api/v1/groups", json={"name": f"pg-group-{suffix}"}
        ).json()["id"]
        user_type_id = client.post(
            "/api/v1/user_types", json={"name": f"pg-user-type-{suffix}"}
        ).json()["id"]
        location_id = client.post(
            "/api/v1/locations", json={"name": f"pg-location-{suffix}"}
        ).json()["id"]
        user_id = f"pg-user-{suffix}"
        user_response = client.post(
            "/api/v1/users",
            json={
                "id": user_id,
                "username": f"PostgreSQL User {suffix}",
                "group_id": group_id,
                "user_type_id": user_type_id,
            },
        )
        assert user_response.status_code == 200

        attendance_date = date(2031, 1, 15).isoformat()
        attendance_response = client.post(
            "/api/v1/attendances",
            data={
                "user_id": user_id,
                "date": attendance_date,
                "location_id": str(location_id),
            },
        )
        assert attendance_response.status_code == 204

        records_response = client.get("/api/v1/attendances")
        assert records_response.status_code == 200
        matching_records = [
            record
            for record in records_response.json()["records"]
            if record["user_id"] == user_id and record["date"] == attendance_date
        ]
        assert len(matching_records) == 1
        assert matching_records[0]["location_id"] == location_id

        duplicate_response = client.post(
            "/api/v1/attendances",
            data={
                "user_id": user_id,
                "date": attendance_date,
                "location_id": str(location_id),
            },
        )
        assert duplicate_response.status_code == 400
