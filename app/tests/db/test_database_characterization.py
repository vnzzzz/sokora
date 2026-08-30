import json
import os
import subprocess
import sys
from pathlib import Path


def test_fresh_database_initialization_creates_seeded_sqlite(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository_root)

    script = r"""
import json
from pathlib import Path

from sqlalchemy import func, select

from app import models
from app.db.session import SessionLocal, initialize_database

assert not list(Path.cwd().rglob("*.db"))
assert initialize_database() is True

created_db_files = [
    str(path.relative_to(Path.cwd())) for path in Path.cwd().rglob("*.db")
]
assert created_db_files

with SessionLocal() as db:
    first_counts = {
        "groups": db.scalar(select(func.count()).select_from(models.Group)),
        "user_types": db.scalar(select(func.count()).select_from(models.UserType)),
        "locations": db.scalar(select(func.count()).select_from(models.Location)),
        "users": db.scalar(select(func.count()).select_from(models.User)),
        "attendances": db.scalar(select(func.count()).select_from(models.Attendance)),
    }

assert initialize_database() is True

with SessionLocal() as db:
    second_attendance_count = db.scalar(
        select(func.count()).select_from(models.Attendance)
    )

print(
    "CHARACTERIZATION="
    + json.dumps(
        {
            "created_db_files": created_db_files,
            "first_counts": first_counts,
            "second_attendance_count": second_attendance_count,
        }
    )
)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout

    output_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("CHARACTERIZATION=")
    )
    observed = json.loads(output_line.removeprefix("CHARACTERIZATION="))
    first_counts = observed["first_counts"]

    assert observed["created_db_files"]
    assert first_counts["groups"] == 3
    assert first_counts["user_types"] == 3
    assert first_counts["locations"] == 4
    assert first_counts["users"] == 5
    assert first_counts["attendances"] > 0
    assert observed["second_attendance_count"] == first_counts["attendances"]
