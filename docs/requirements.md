# 要件ドキュメント

sokora の API・DB・UI・production runtimeを横断的に把握するための要件集約ドキュメントです。詳細は分野別ドキュメントに委譲し、重複を避けます。

## ドキュメント一覧
- [API 要件](api/requirements.md)
- [DB 要件](db/requirements.md)
- [UI 要件](ui/requirements.md)
- [テンプレート構成](ui/templates.md)（UI のファイル配置の補足）
- [Production container runtime contract](deployment/runtime.md)

## 共通方針
- FastAPI（/api プレフィックス）と Jinja2 + HTMX/Alpine.js の SSR UI を整合させる。
- 勤怠・ユーザー・マスタ（勤怠種別/社員種別/グループ）の整合性は DB モデルを基準に、API と UI の期待値を合わせる。
- DB接続は `DATABASE_URL` をSSoTとし、local/閉域ではSQLiteを維持しつつ、外部/managed DBとしてPostgreSQLを利用できる。schema lifecycleは両backendでAlembicへ統一する。
- production runtimeはprovider非依存のOCI imageとし、閉域/GCP/AWS/Azure固有差分をdeployment adapterへ閉じ込める。application/DB access層はcloud provider固有SDKへ依存しない。
- 振る舞いの詳細は分野別ドキュメントを参照し、記述が無い場合はテストや実装を一次情報として更新する。

## 認証方針
- 標準OIDCを一次認証経路とし、local adminだけが使える管理用fallbackを併置する。自動failoverは行わず、login画面で利用者が明示的に選択する。
- OIDC clientはAuthlibを利用し、`OIDC_ISSUER` のOpenID Provider Configurationからauthorization/token/JWKS/logout metadataをdiscoveryする。Keycloak固有endpoint pathをapplicationで組み立てず、一般的なOIDC providerへ適用可能な境界とする。
- OIDC設定（issuer/client_id/client_secret/redirect_uri/scope/timeout）はruntimeのenvironment/secret injectionで管理し、replica-local mutable fileやruntime toggleを共有設定として利用しない。
- sessionはStarletteの署名付きclient-side cookie。永続cookieには認証方式・OIDC subject・表示username・admin role等の最小identityだけを保持し、OIDC access/refresh/ID tokenは保持しない。OAuth state / OIDC nonceは認証flow中だけ一時的に保持する。
- session cookieはHttpOnly + SameSite=Laxを基本とし、HTTPS productionでは`SOKORA_AUTH_SESSION_HTTPS_ONLY=true`にしてSecure属性を必須とする。既定TTLは1時間で、期限切れ時は再loginさせる。
- OIDC user識別子は検証済みID tokenの`sub`を利用し、`preferred_username`等は表示用。現時点ではapplicationの`users` tableとは紐付けない。
- admin-only routeは共通authorization policyで保護し、認証後redirect先はsame-origin pathだけを許可する。
