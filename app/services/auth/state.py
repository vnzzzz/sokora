import json
import logging
from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuthState:
    oidc_enabled: bool = True


class AuthStateStore:
    """OIDC 有効/無効状態をファイルに保持するシンプルなストア"""

    def __init__(self, path: Path | None = None) -> None:
        env_path = environ.get("SOKORA_AUTH_STATE_PATH")
        resolved = Path(env_path) if env_path else path
        self.path = resolved or Path("data/auth_state.json")

    def load_state(self) -> AuthState:
        if not self.path.exists():
            return AuthState()
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                data: dict[str, Any] = json.load(fp)
            return AuthState(oidc_enabled=bool(data.get("oidc_enabled", True)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load auth state, fallback to defaults: %s", exc)
            return AuthState()

    def save_state(self, state: AuthState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fp:
            json.dump({"oidc_enabled": state.oidc_enabled}, fp)
