import os
import subprocess
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MISSING_ENV_FILE = ".env.makefile-contract-test-missing"


def _run_make(
    *args: str,
    dry_run: bool = False,
    env_file: str = _MISSING_ENV_FILE,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in ("VERSION", "SERVICE_PORT", "PORT", "proxy"):
        env.pop(name, None)

    command = ["make", "--no-print-directory"]
    if dry_run:
        command.append("-n")
    command.extend([f"ENV_FILE={env_file}", *args])
    return subprocess.run(
        command,
        cwd=_REPOSITORY_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_development_run_does_not_require_version_and_uses_default_port() -> None:
    result = _run_make("run", dry_run=True, env_file=".env.sample")

    assert result.returncode == 0, result.stderr
    assert "uvicorn app.main:app" in result.stdout
    assert "--port 8000 --reload" in result.stdout


def test_versioned_image_target_requires_version() -> None:
    result = _run_make("docker-build")

    assert result.returncode != 0
    assert "VERSION is required for versioned image/package targets" in result.stderr
    assert "docker build" not in result.stdout


def test_help_states_docker_run_version_requirement() -> None:
    result = _run_make("help")

    assert result.returncode == 0, result.stderr
    assert "make docker-run" in result.stdout
    assert "requires VERSION" in next(
        line for line in result.stdout.splitlines() if "make docker-run" in line
    )


def test_docker_run_forwards_only_explicit_application_environment() -> None:
    result = _run_make(
        "VERSION=test",
        "docker-run",
        dry_run=True,
        env_file=".env.sample",
    )

    assert result.returncode == 0, result.stderr
    assert "--env-file" not in result.stdout

    docker_run = result.stdout.split("docker run", maxsplit=1)[1]
    assert "-e DATABASE_URL" in docker_run
    assert "-e SOKORA_AUTH_ENABLED" in docker_run
    assert "-e OIDC_REDIRECT_URL" in docker_run
    assert "-e VERSION" not in docker_run
    assert "-e SERVICE_PORT" not in docker_run
