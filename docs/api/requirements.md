# API 要件

FastAPI v1 ルーター（`app/routers/api/v1/__init__.py`）配下で `/api/v1` プレフィックスを使用します。データモデルは [DB 要件](../db/requirements.md) を基準とし、UI 側の HTMX フローは [UI 要件](../ui/requirements.md) を参照してください。

## 共通仕様
- `/api/v1/*` は JSON API contract を担当し、HTML fragment・Form adapter・`HX-*` response header を持たない。
- page/HTMX endpoint は `app/routers/pages/` 配下へ置き、OpenAPIへ含めない。UI formをapplication schemaへ変換し、APIと同じservice/use caseを呼ぶ。
- write use case は service 層が transaction を所有し、CRUD 層は commit/rollback を行わない。事前バリデーションに加えて DB の UNIQUE / FK 制約を最終整合性保証とする。
- 事前チェックで判定できる既存の入力不備・重複は 400/404 等を返す。concurrent write 等で commit/flush 時に DB integrity constraint と競合した場合は application error へ変換し、409 を返す。DB 例外文字列は外部へ直接公開しない。
- OpenAPI は `/docs` `/redoc` で公開される。
- 認証は標準OIDCを一次経路とし、管理者のみが使えるlocal loginを併置する。自動failoverは行わず、ログイン画面で利用者が選択する。

## 認証/セキュリティ
- ガード: `SOKORA_AUTH_ENABLED=true` 時に UI/`/api` 双方へsession guardを適用し、未認証アクセスは UI → `/auth/login` へredirect、API → 401 JSON（`{"detail": "Unauthorized"}`）を返す。`/auth/*` と静的ファイル、`/docs`/`/redoc` は例外。
- session:
  - Starlette `SessionMiddleware` の署名付きclient-side cookieを利用する。server-side session storeではない。
  - `SOKORA_AUTH_SESSION_SECRET` で署名鍵、`SOKORA_AUTH_SESSION_TTL_SECONDS`（default 3600秒）で有効期限を指定する。
  - SameSiteは`lax`、HttpOnlyは常時有効。`SOKORA_AUTH_SESSION_HTTPS_ONLY=true` でSecure cookieを有効化し、HTTPS productionではtrueを必須とする。
  - 認証後cookieに保持するのは認証方式・subject・表示username・admin role等の最小identity情報だけで、OIDC access token / refresh token / ID tokenは保持しない。
- OIDC:
  - AuthlibのStarlette integrationを利用する。
  - 設定は `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URL`, `OIDC_SCOPES`（default `openid profile email`）, `OIDC_HTTP_TIMEOUT`（default 3s）。
  - issuerの `/.well-known/openid-configuration` によるdiscoveryを使用し、authorization/token/JWKS/end-session endpointをapplicationで手組みしない。
  - `/auth/redirect` からauthorization code flowを開始する。OAuth state / OIDC nonceはAuthlibがsigned sessionへ一時保存し、`/auth/callback` でstateを照合したうえでcode exchangeとID token検証を行う。
  - ID tokenのissuer/audience/signature/expiry/nonce等はdiscovery metadata/JWKSとAuthlibのOIDC validationに委譲する。検証済み`userinfo`の`sub`を内部識別子、`preferred_username`（fallback: email/name/sub）を表示名としてsessionへ投影する。DB `users` tableとは紐付けない。
  - `next` parameterはsame-origin absolute pathだけを許可し、absolute URL、scheme-relative URL（`//host/...`）、backslashを含む値等は `/` へfallbackする。
- logout:
  - `/auth/logout` でapplication認証sessionを破棄する。
  - discovery metadataに`end_session_endpoint`がある場合はRP-Initiated Logoutへredirectし、`/auth/logout/callback` でlogout stateを検証する。
  - persistent cookieへID tokenを保持しないためlogoutは`client_id` + registered `post_logout_redirect_uri`を利用し、`id_token_hint`へ依存しない。IdPの追加confirmation/policyはprovider設定側で扱う。
  - end-session endpointが無い、またはprovider logoutが利用できない場合もapplication sessionは破棄する。
- local admin login:
  - `SOKORA_LOCAL_AUTH_ENABLED=true` かつ `SOKORA_LOCAL_ADMIN_USERNAME`, `SOKORA_LOCAL_ADMIN_PASSWORD` が揃っている場合だけ有効。入力値は`secrets.compare_digest`で照合し、成功時は`role=admin`を持つsessionを発行する。
  - OIDC障害時でもlocal admin経路を明示的に選択できる。一般ユーザー向けlocal loginや自動failoverは提供しない。
  - admin-only routeは共通authorization dependencyで保護する。
- runtime設定:
  - 認証設定はenvironment/secret injectionをSSoTとし、`auth_state.json`等のreplica-local mutable fileは利用しない。
  - `/auth/settings` はlocal admin向けread-only diagnosticsで、runtime OIDC toggleは提供しない。

## エンドポイント一覧（v1）
- `GET /api/v1/attendances`：全勤怠リスト（`{"records": [...]}`）。
- `GET /api/v1/attendances/day/{day}`：日付別の勤怠詳細をロケーション軸でJSON返却。
- `POST /api/v1/attendances`：`AttendanceCreate` JSONを受付し201 + 作成レコードを返す。ユーザー + 日付の重複を禁止し、DBの`UNIQUE(user_id, date)`でも保証する。
- `PUT /api/v1/attendances/{attendance_id}`：`AttendanceUpdate` JSONを受付し200 + 更新レコードを返す。
- `DELETE /api/v1/attendances/{attendance_id}`：ID指定削除、204。
- `DELETE /api/v1/attendances?user_id=...&date=...`：ユーザー + 日付指定削除、204。
- `GET /api/v1/users` / `GET /api/v1/users/{user_id}`：社員一覧・単体取得。`{"users": [...]}` 形式。
- `POST /api/v1/users`：社員作成（JSON）。グループ・社員種別の存在確認と重複チェックをサービス層で実施し、DB FK を最終保証とする。
- `PUT /api/v1/users/{user_id}`：社員更新。
- `DELETE /api/v1/users/{user_id}`：関連勤怠削除とユーザー削除を同一 transaction で実行して 204 を返す。途中失敗時は全体を rollback する。
- `GET /api/v1/locations`：勤怠種別一覧を名前順で返す。
- `POST /api/v1/locations` / `PUT /api/v1/locations/{location_id}`：勤怠種別の作成・更新。サービス層で重複/参照チェック。
- `DELETE /api/v1/locations/{location_id}`：勤怠種別削除。利用中チェックに加えて DB FK で参照整合性を保証。
- `GET /api/v1/groups`：グループ一覧（order → name の順でソート）。
- `POST /api/v1/groups` / `PUT /api/v1/groups/{group_id}` / `DELETE /api/v1/groups/{group_id}`：グループ CRUD。
- `GET /api/v1/user_types`：社員種別一覧（order → name でソート）。
- `POST /api/v1/user_types` / `PUT /api/v1/user_types/{user_type_id}` / `DELETE /api/v1/user_types/{user_type_id}`：社員種別 CRUD。
- `GET /api/v1/csv/download?month=YYYY-MM&encoding=utf-8|sjis`：勤怠データをストリーミング出力。エンコーディング検証と月フォーマット検証を実施。Content-Disposition でファイル名を付与。

## UI 連携の留意点
- 勤怠modalのwriteは `/attendance/entries` page/HTMX adapterを利用する。成功時は `HX-Trigger` (`closeModal` / `refreshUserAttendance` / `refreshAttendance`) を返す。month/weekは変更対象の勤怠日から導出し、`Referer`やテスト専用headerへ依存しない。
- HTMX writeでapplication errorが発生した場合はHTML fragmentとしてmodal内のerror領域へretargetする。JSON APIのerror responseをHTML targetへ流用しない。
- `/api/v1/csv/download` は `pages/csv.html` からクエリストリングを組み立ててダウンロードする。
- API が前提とするフィールド名や型は [DB 要件](../db/requirements.md) のモデル構成に従う。
