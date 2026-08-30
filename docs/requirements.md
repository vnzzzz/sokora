# 要件ドキュメント

sokora の API・DB・UI を横断的に把握するための要件集約ドキュメントです。詳細は分野別ドキュメントに委譲し、重複を避けます。

## ドキュメント一覧
- [API 要件](api/requirements.md)
- [DB 要件](db/requirements.md)
- [UI 要件](ui/requirements.md)
- [テンプレート構成](ui/templates.md)（UI のファイル配置の補足）

## 共通方針
- FastAPI（/api プレフィックス）と Jinja2 + HTMX/Alpine.js の SSR UI を整合させる。
- 勤怠・ユーザー・マスタ（勤怠種別/社員種別/グループ）の整合性は DB モデルを基準に、API と UI の期待値を合わせる。
- 振る舞いの詳細は分野別ドキュメントを参照し、記述が無い場合はテストや実装を一次情報として更新する。

## 認証方針
- IdP に Keycloak を用いた OIDC を一次経路とし、ローカル管理者のみが使える代替ログイン経路を併置する。自動フェイルオーバーは行わず、ログイン画面で手動選択させる。
- OIDC 設定（issuer/client_id/client_secret/redirect_uri/scope/タイムアウトなど）は `.env` に `OIDC_*` で管理し、Keycloak 障害（HTTP 5xx / タイムアウト）発生時はエラーを提示した上でローカル管理者経路を案内する。
- OIDC 有効/無効はローカル管理者専用ページでトグルでき、状態は `data/auth_state.json` に保持する。
- セッションはアプリ側のサーバーセッションで管理し、デフォルト有効期限は 1 時間。リフレッシュトークンは保持せず、期限切れ時は再ログインさせる。
- ユーザー識別子は Keycloak の `sub` を優先し、`preferred_username` は表示用。現時点ではアプリ内の `users` テーブルとは紐付けない。
