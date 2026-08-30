import os
import subprocess
import sys
from pathlib import Path


def test_alembic_accepts_database_url_with_percent_sign(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    database_path = tmp_path / "sokora%test.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path}"
    environment["PYTHONPATH"] = str(repository_root)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "scripts/migration/alembic.ini",
            "current",
        ],
        cwd=repository_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert database_path.exists()
