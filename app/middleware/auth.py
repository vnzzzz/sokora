"""authentication guardをUI/API共通のrequest boundaryとして適用する。"""

import logging
import urllib.parse
from typing import Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp

from app.services.auth.settings import AuthSettings

logger = logging.getLogger(__name__)


def _is_exempt_path(path: str, exempt_prefixes: Iterable[str]) -> bool:
    return any(path.startswith(prefix) for prefix in exempt_prefixes)


class AuthRequiredMiddleware(BaseHTTPMiddleware):
    """signed sessionの有無をUI/API共通のauthentication boundaryとして強制する。

    ``auth_enabled=false`` ではrequestをそのまま通す。guard有効時もlogin/static/health/
    OpenAPI等の明示prefixはsessionなしで到達可能にし、それ以外はsessionの ``auth``
    identityを要求する。

    未認証APIはredirectせず401 JSONを返し、browser pageは元のrelative path/queryを
    ``next`` としてloginへ307 redirectする。ここではadmin role等のauthorizationまでは
    判定せず、admin-only policyはdependency側へ分離する。
    """

    def __init__(
        self,
        app: ASGIApp,
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
                "/healthz",
                "/docs",
                "/redoc",
                "/openapi.json",
            )
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """request時点のsettings provider結果とsigned sessionからguard結果を決定する。

        settings providerは毎request評価する。一方、SessionMiddlewareのsecret/cookie設定は
        application作成時に固定されるため、provider値だけをrunning process内で変更する
        hot-reconfigurationはsupportしない。runtime config変更はprocess restartで全middleware
        へ同じ設定を適用する。

        認証identityの形式はSessionMiddlewareが検証したsession mappingだけを信頼する。
        exempt pathは「公開してよいendpoint」のcontractなので、機能routeを追加する目的だけで
        安易にprefixを広げない。
        """
        settings = self.settings_provider()
        if not settings.auth_enabled:
            return await call_next(request)

        path = request.url.path
        if _is_exempt_path(path, self.exempt_prefixes):
            return await call_next(request)

        if request.session.get("auth"):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        is_htmx = request.headers.get("HX-Request") == "true"
        next_path = (
            self._build_htmx_next_path(request)
            if is_htmx
            else self._build_next_path(request)
        )
        login_url = f"/auth/login?next={urllib.parse.quote(next_path)}&reason=reauth"
        if is_htmx:
            return Response(status_code=200, headers={"HX-Redirect": login_url})
        return RedirectResponse(url=login_url, status_code=307)

    def _build_htmx_next_path(self, request: Request) -> str:
        """HTMX fragment requestではbrowserのpage-level URLをlogin後の戻り先にする。

        ``HX-Current-URL`` はbrowser address barのURLなので、same-originを確認してから
        relative path/queryへ落とす。headerが欠ける・不正な場合はsame-origin Refererを
        fallbackとして使い、それも利用できなければrequest pathだけへ戻す。fragment request
        自身のqueryは一時UI stateを含み得るためfallbackへ流用しない。
        """
        request_url = urllib.parse.urlsplit(str(request.url))
        for header_name in ("HX-Current-URL", "Referer"):
            candidate = request.headers.get(header_name)
            if not candidate:
                continue

            parsed = urllib.parse.urlsplit(candidate)
            if (
                parsed.scheme != request_url.scheme
                or parsed.netloc != request_url.netloc
                or not parsed.path.startswith("/")
                or parsed.path.startswith("//")
            ):
                continue

            path = parsed.path or "/"
            if parsed.query:
                return f"{path}?{parsed.query}"
            return path

        return request.url.path

    def _build_next_path(self, request: Request) -> str:
        """元requestのrelative path/queryだけからlogin後の戻り先を構成する。

        scheme/hostを取り込まないため、このmiddleware自身が生成する ``next`` が外部URLに
        なることを防ぐ。最終的なnext path validationはlogin/callback側のboundaryでも行う。
        """
        path = request.url.path
        query = request.url.query
        if not query:
            return path
        return f"{path}?{query}"
