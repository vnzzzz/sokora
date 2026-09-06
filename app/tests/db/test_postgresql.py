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
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.core.settings import AppSettings
from app.db.session import (
    _database_url_for_logging,
    _postgresql_readiness_connect_args,
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


def test_postgresql_readiness_preserves_configured_libpq_options() -> None:
    url = sqlalchemy_database_url(
        "postgresql://sokora@db.example/sokora" "?options=-c%20search_path%3Dsokora"
    )

    connect_args = _postgresql_readiness_connect_args(url)

    assert connect_args["connect_timeout"] == 2
    assert connect_args["options"] == "-c search_path=sokora -c statement_timeout=2000"


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


def test_postgresql_readiness_requires_application_schema() -> None:
    database_url = os.getenv("SOKORA_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("SOKORA_TEST_POSTGRES_URL is not configured")

    url = make_url(database_url)
    query = dict(url.query)
    query["options"] = "-c search_path=sokora_readiness_missing_schema"
    probe_database_url = url.set(query=query).render_as_string(hide_password=False)
    runtime = create_database_runtime(probe_database_url)
    try:
        assert runtime.probe_readiness() is False
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
        assert client.delete(f"/api/v1/groups/{disposable_group_id}").status_code == 204

        group_id = client.post(
            "/api/v1/groups", json={"name": f"pg-group-{suffix}"}
        ).json()["id"]
        user_type_id = client.post(
            "/api/v1/user_types", json={"name": f"pg-user-type-{suffix}"}
        ).json()["id"]
        location_id = client.post(
            "/api/v1/locations", json={"name": f"pg-location-{suffix}"}
        ).json()["id"]

        calendar_response = client.get("/calendar", params={"month": "2031-01"})
        assert calendar_response.status_code == 200
        user_id = f"pg-user-{suffix}"
        username = f"PostgreSQL User {suffix}"
        user_response = client.post(
            "/api/v1/users",
            json={
                "id": user_id,
                "username": username,
                "group_id": group_id,
                "user_type_id": user_type_id,
            },
        )
        assert user_response.status_code == 200

        user_constraints = inspect(runtime.engine).get_unique_constraints("users")
        assert any(
            constraint["name"] == "uq_users_username"
            and set(constraint["column_names"]) == {"username"}
            for constraint in user_constraints
        )
        with runtime.session_factory() as db:
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        "insert into users (id, username, group_id, user_type_id) "
                        "values (:id, :username, :group_id, :user_type_id)"
                    ),
                    {
                        "id": f"{user_id}-duplicate",
                        "username": username,
                        "group_id": group_id,
                        "user_type_id": user_type_id,
                    },
                )
                db.commit()
            db.rollback()

        attendance_date = date(2031, 1, 15).isoformat()
        attendance_payload = {
            "user_id": user_id,
            "date": attendance_date,
            "location_id": location_id,
        }
        attendance_response = client.post(
            "/api/v1/attendances", json=attendance_payload
        )
        assert attendance_response.status_code == 201

        records_response = client.get("/api/v1/attendances")
        assert records_response.status_code == 200
        matching_records = [
            record
            for record in records_response.json()["records"]
            if record["user_id"] == user_id and record["date"] == attendance_date
        ]
        assert len(matching_records) == 1
        assert matching_records[0]["location_id"] == location_id

        duplicate_response = client.post("/api/v1/attendances", json=attendance_payload)
        assert duplicate_response.status_code == 400
