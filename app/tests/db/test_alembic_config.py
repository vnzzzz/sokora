import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_head_builds_fresh_database_with_percent_sign(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    database_path = tmp_path / "sokora%test.db"
    database_url = f"sqlite:///{database_path}"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment["PYTHONPATH"] = str(repository_root)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "scripts/migration/alembic.ini",
            "upgrade",
            "head",
        ],
        cwd=repository_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert database_path.exists()

    engine = create_engine(database_url)
    try:
        table_names = inspect(engine).get_table_names()
        assert "alembic_version" in table_names
        assert "groups" in table_names
        assert "attendance" in table_names
        assert "custom_holidays" in table_names
        with engine.connect() as connection:
            assert connection.scalar(text("select version_num from alembic_version"))
    finally:
        engine.dispose()
