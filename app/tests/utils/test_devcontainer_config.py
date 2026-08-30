from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEVCONTAINER_JSON = REPO_ROOT / ".devcontainer" / "devcontainer.json"
DEVCONTAINER_DOCKERFILE = REPO_ROOT / ".devcontainer" / "Dockerfile"
DEVCONTAINER_VOLUME_OWNERSHIP_SCRIPT = (
    REPO_ROOT / ".devcontainer" / "ensure-volume-ownership.sh"
)
AGENT_DEV_FEATURE = "ghcr.io/vnzzzz/agentic-development-toolkit/agent-dev:1"


def load_devcontainer_config() -> dict[str, Any]:
    return json.loads(DEVCONTAINER_JSON.read_text())


def test_devcontainer_does_not_forward_ports_by_default() -> None:
    config = load_devcontainer_config()
    forward_ports = config.get("forwardPorts")

    assert forward_ports in (None, []), "forwardPorts should be unset to avoid port use on startup"


def test_devcontainer_uses_shared_agent_dev_feature() -> None:
    config = load_devcontainer_config()

    assert config["features"] == {AGENT_DEV_FEATURE: {}}
    assert config["remoteUser"] == "vscode"
    assert "postCreateCommand" not in config

    mounts = config.get("mounts", [])
    assert all("/root/" not in mount for mount in mounts)
    assert any("/home/vscode/.cache/pypoetry" in mount for mount in mounts)


def test_devcontainer_does_not_install_agent_tools_directly() -> None:
    config_text = DEVCONTAINER_JSON.read_text()
    dockerfile = DEVCONTAINER_DOCKERFILE.read_text()

    assert "ghcr.io/devcontainers/features/node:1" not in config_text
    assert "ghcr.io/devcontainers/features/github-cli:1" not in config_text
    assert "@openai/codex" not in config_text
    assert "@openai/codex" not in dockerfile
    assert "@anthropic-ai/claude-code" not in dockerfile


def test_devcontainer_runtime_paths_support_vscode_user() -> None:
    dockerfile = DEVCONTAINER_DOCKERFILE.read_text()

    assert "POETRY_HOME=/opt/poetry" in dockerfile
    assert "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" in dockerfile
    assert "/home/vscode/.cache/pypoetry" in dockerfile


def test_devcontainer_repairs_persisted_volume_ownership_after_start() -> None:
    config = load_devcontainer_config()
    script = DEVCONTAINER_VOLUME_OWNERSHIP_SCRIPT.read_text()

    assert config["postStartCommand"] == "bash .devcontainer/ensure-volume-ownership.sh"
    assert "id -u" in script
    assert "id -g" in script
    assert "sudo chown -R" in script
    assert "/app/data" in script
    assert "/home/vscode/.cache/pypoetry" in script


def test_devcontainer_cmd_is_idle_until_server_runs() -> None:
    dockerfile = DEVCONTAINER_DOCKERFILE.read_text()
    cmd_lines = [
        line.strip() for line in dockerfile.splitlines() if line.strip().startswith("CMD")
    ]

    assert cmd_lines, "CMD must be defined in devcontainer Dockerfile"

    cmd_line = cmd_lines[-1]
    assert "sleep" in cmd_line and "infinity" in cmd_line
    assert "uvicorn" not in cmd_line, "webserver should start via make run instead of devcontainer CMD"
