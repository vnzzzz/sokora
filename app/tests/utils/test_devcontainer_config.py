from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_devcontainer_does_not_forward_ports_by_default() -> None:
    devcontainer_json = REPO_ROOT / ".devcontainer" / "devcontainer.json"
    config = json.loads(devcontainer_json.read_text())
    forward_ports = config.get("forwardPorts")

    assert forward_ports in (None, []), "forwardPorts should be unset to avoid port use on startup"


def test_devcontainer_cmd_is_idle_until_server_runs() -> None:
    dockerfile = (REPO_ROOT / ".devcontainer" / "Dockerfile").read_text()
    cmd_lines = [
        line.strip() for line in dockerfile.splitlines() if line.strip().startswith("CMD")
    ]

    assert cmd_lines, "CMD must be defined in devcontainer Dockerfile"

    cmd_line = cmd_lines[-1]
    assert "sleep" in cmd_line and "infinity" in cmd_line
    assert "uvicorn" not in cmd_line, "webserver should start via make run instead of devcontainer CMD"
