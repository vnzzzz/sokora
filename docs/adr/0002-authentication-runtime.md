# 0002: Provider-neutral OIDC + signed client-side session

**Status:** Accepted

## 背景

ADR 0001 では Keycloak 固定、server-side session、file-backed runtime toggle を前提としていた。しかし、production runtime を provider 非依存に保ち、複数 replica 間で共有できない mutable auth state を排除しつつ、標準 OIDC provider へ適用できる認証境界が必要になった。

## 決定

- 一般ユーザーの一次認証経路は標準 OIDC Authorization Code flow とする。local login は管理者専用 fallback とし、自動 failover は行わない。
- OIDC client は Authlib を使用し、`OIDC_ISSUER` の OpenID Provider Configuration から authorization / token / JWKS / end-session metadata を discovery する。Keycloak 固有 endpoint path を application で組み立てない。
- OIDC 設定は environment / secret injection を SSoT とする。`auth_state.json` 等の replica-local mutable file や runtime OIDC toggle は共有設定として利用しない。
- `/auth/settings` は local admin 向けの read-only diagnostics とし、認証方式を runtime 変更する UI は提供しない。
- session は Starlette `SessionMiddleware` の署名付き client-side cookie とする。永続 cookie には認証方式、OIDC `sub`、表示 username、admin role 等の最小 identity だけを保持し、OIDC access token / refresh token / ID tokenは保持しない。
- OAuth state / OIDC nonce は認証 flow 中だけ session に一時保持し、callback で state と ID token を検証する。OIDC identity は検証済み `userinfo` の `sub` を基準とし、現時点では application の `users` table と紐付けない。
- session cookie は HttpOnly + SameSite=Lax を基本とし、HTTPS production では `SOKORA_AUTH_SESSION_HTTPS_ONLY=true` にして Secure 属性を必須とする。既定 TTL は 1 時間とする。
- 認証後の `next` は same-origin absolute path のみに制限し、外部 URL や scheme-relative URL 等は `/` へ fallback する。
- logout は application session を必ず破棄する。discovery metadata に `end_session_endpoint` がある場合は RP-Initiated Logout を利用し、provider logout が無い・失敗した場合も local session logout は成立させる。
- local admin は `SOKORA_LOCAL_AUTH_ENABLED=true` かつ username/password が設定されている場合だけ有効化し、admin-only route は共通 authorization dependency で保護する。

## 影響

- Keycloak は利用可能な OIDC provider の一つであり、application architecture上の必須 provider ではない。
- 認証設定変更は environment / secret の更新と application 再起動・再デプロイを通じて行う。application 内の file-backed toggle は持たない。
- 認証済み session は各 replica のローカルファイルに依存しない。ただし application 全体の multi-replica consistency は、認証以外の process-local state を扱う #86 の完了まで保証しない。
- 詳細な runtime/API/UI contract は `docs/requirements.md`、`docs/api/requirements.md`、`docs/ui/requirements.md`、`docs/deployment/runtime.md` を SSoT とする。

## Supersedes

- [ADR 0001: Keycloak OIDC + ローカル管理者フォールバックの採用](0001-authentication.md)
