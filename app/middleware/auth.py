import logging
import urllib.parse
from typing import Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.services.auth.settings import AuthSettings

logger = logging.getLogger(__name__)


def _is_exempt_path(path: str, exempt_prefixes: Iterable[str]) -> bool:
    return any(path.startswith(prefix) for prefix in exempt_prefixes)


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    """セッションを前提に UI/API 双方へ認証ガードを適用するミドルウェア"""

    def __init__(
        self,
        app,
        settings_provider: Callable[[], AuthSettings],
        exempt_prefixes: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.settings_provider = settings_provider
        self.exempt_prefixes = tuple(
            exempt_prefixes
            or (
                "/auth",
                "/assets",
                "/static",
                "/favicon.ico",
                "/docs",
                "/redoc",
                "/openapi.json",
            )
        )

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        settings = self.settings_provider()
        if not settings.auth_required:
            return await call_next(request)

        path = request.url.path
        if _is_exempt_path(path, self.exempt_prefixes):
            return await call_next(request)

        if request.session.get("auth"):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        next_path = self._build_next_path(request)
        login_url = f"/auth/login?next={urllib.parse.quote(next_path)}&reason=reauth"
        return RedirectResponse(url=login_url, status_code=307)

    def _build_next_path(self, request: Request) -> str:
        """クエリ付きのリダイレクト先を安全に構成する"""
        path = request.url.path
        query = request.url.query
        if not query:
            return path
        return f"{path}?{query}"
