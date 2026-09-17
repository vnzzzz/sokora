import os
import subprocess
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MISSING_ENV_FILE = ".env.makefile-contract-test-missing"


def _run_make(
    *args: str,
    context: str | None = None,
    dry_run: bool = False,
    env_file: str = _MISSING_ENV_FILE,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for name in ("VERSION", "SERVICE_PORT", "PORT", "proxy", "SOKORA_MAKE_CONTEXT"):
        env.pop(name, None)

    command = ["make", "--no-print-directory"]
    if dry_run:
        command.append("-n")
    if context is not None:
        command.append(f"SOKORA_MAKE_CONTEXT={context}")
    command.extend([f"ENV_FILE={env_file}", *args])
    return subprocess.run(
        command,
        cwd=_REPOSITORY_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_default_context_exposes_only_docker_host_targets() -> None:
    result = _run_make("help")

    assert result.returncode == 0, result.stderr
    assert "Sokora Docker host targets:" in result.stdout
    assert "make docker-run" in result.stdout
    assert "  make run " not in result.stdout


def test_workspace_context_exposes_only_workspace_targets() -> None:
    result = _run_make("help", context="workspace")

    assert result.returncode == 0, result.stderr
    assert "Sokora workspace targets:" in result.stdout
    assert "  make run " in result.stdout
    assert "make docker-run" not in result.stdout


def test_host_context_rejects_workspace_target() -> None:
    result = _run_make("run", dry_run=True)

    assert result.returncode != 0
    assert "No rule to make target 'run'" in result.stderr


def test_workspace_context_rejects_host_target() -> None:
    result = _run_make("docker-build", context="workspace", dry_run=True)

    assert result.returncode != 0
    assert "No rule to make target 'docker-build'" in result.stderr


def test_unknown_context_fails_during_makefile_loading() -> None:
    result = _run_make("help", context="unknown")

    assert result.returncode != 0
    assert "SOKORA_MAKE_CONTEXT must be 'workspace' or 'host'" in result.stderr


def test_development_run_does_not_require_version_and_uses_default_port() -> None:
    result = _run_make(
        "run",
        context="workspace",
        dry_run=True,
        env_file=".env.sample",
    )

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


def test_dev_build_uses_repository_root_as_build_context() -> None:
    result = _run_make("dev-build", dry_run=True)

    assert result.returncode == 0, result.stderr
    assert "docker build -f .devcontainer/Dockerfile -t sokora-dev ." in result.stdout
    assert "sokora-dev .." not in result.stdout


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
