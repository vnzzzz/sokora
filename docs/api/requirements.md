# API 要件

 FastAPI v1 ルーター（`app/routers/api/v1/__init__.py`）配下で `/api/v1` プレフィックスを使用します。データモデルは [DB 要件](../db/requirements.md) を基準とし、UI 側の HTMX フローは [UI 要件](../ui/requirements.md) を参照してください。

## 共通仕様
- 応答は原則 JSON。勤怠作成/更新/削除はフォーム送信を受け、204 + `HX-Trigger` で UI 更新を指示。
- 外部連携や認可は未実装。バリデーションはサービス/CRUD層で外部キー整合性や重複を確認。
- OpenAPI は `/docs` `/redoc` で公開される。
- 認証は Keycloak OIDC を一次経路とし、管理者のみが使えるローカルログインを併置する。自動フェイルオーバーは行わず、ログイン画面で利用者が選択する。

## 認証/セキュリティ
- ガード: `SOKORA_AUTH_ENABLED=true` 時に UI/`/api` 双方へセッションガードを適用し、未認証アクセスは UI → `/auth/login` へリダイレクト、API → 401 JSON（`{"detail": "Unauthorized"}`）を返す。`/auth/*` と静的ファイル、`/docs`/`/redoc` は例外。
- セッション: Starlette セッションで管理。`SOKORA_AUTH_SESSION_SECRET` で署名鍵、`SOKORA_AUTH_SESSION_TTL_SECONDS`（デフォルト 3600 秒）で有効期限を指定。
- Keycloak OIDC:
  - `.env` 設定: `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URL`, `OIDC_SCOPES`（デフォルト `openid profile email`）, 任意で `OIDC_AUTHORIZATION_ENDPOINT`, `OIDC_TOKEN_ENDPOINT`, `OIDC_USERINFO_ENDPOINT`, `OIDC_LOGOUT_ENDPOINT`, `OIDC_HTTP_TIMEOUT`（デフォルト 3s）。
- フロー: `/auth/redirect` で state/nonce を発行し Keycloak 認可エンドポイントへリダイレクト、`/auth/callback` でコードをトークンエンドポイントへ POST。`id_token` の `sub` を内部識別子、`preferred_username` を表示名としてセッションに格納する。DB の `users` テーブルとは紐付けない。
  - ログアウト: `/auth/logout` でアプリセッションを破棄し、`SOKORA_OIDC_LOGOUT_ENDPOINT` がある場合は `id_token_hint`/`post_logout_redirect_uri` を付けて Keycloak ログアウトに誘導する。
- OIDC 有効/無効トグル:
  - ローカル管理者専用ページで切替可能。状態は `data/auth_state.json`（`SOKORA_AUTH_STATE_PATH` で上書き可）に保持し、`oidc_enabled=false` の場合は OIDC フローを開始せず 400 を返す。
- ローカル管理者ログイン:
  - 環境変数 `SOKORA_LOCAL_AUTH_ENABLED` が true かつ `SOKORA_LOCAL_ADMIN_USERNAME`, `SOKORA_LOCAL_ADMIN_PASSWORD` が揃っている場合のみ有効。入力値は `secrets.compare_digest` で照合し、成功時は `role=admin` を持つセッションを発行する。
  - Keycloak 障害時でもログイン画面のローカル経路は常に提示する。一般ユーザー向けのローカルログインは提供しない。
  - 設定欠落時は 400 を返し、ログイン画面にエラーを表示する。

## エンドポイント一覧（v1）
- `GET /api/v1/attendances`：全勤怠リスト（`{"records": [...]}`）。  
- `GET /api/v1/attendances/day/{day}`：日付別の勤怠詳細をロケーション軸で返却。  
- `POST /api/v1/attendances`：`user_id`・`date`（YYYY-MM-DD）・`location_id`・`note?` をフォームで受付。ユーザー + 日付の重複を禁止。成功時はモーダル閉鎖と当月再読み込みを `HX-Trigger` で通知。  
- `PUT /api/v1/attendances/{attendance_id}`：勤怠種別や備考を更新。`HX-Trigger` で対象ユーザー/月の再描画を要求。  
- `DELETE /api/v1/attendances/{attendance_id}`：ID指定削除。  
- `DELETE /api/v1/attendances?user_id=...&date=...`：ユーザー + 日付指定削除。  
- `GET /api/v1/users` / `GET /api/v1/users/{user_id}`：社員一覧・単体取得。`{"users": [...]}` 形式。  
- `POST /api/v1/users`：社員作成（JSON）。グループ・社員種別の存在確認と重複チェックをサービス層で実施。  
- `PUT /api/v1/users/{user_id}`：社員更新。  
- `DELETE /api/v1/users/{user_id}`：関連勤怠を先に削除してからユーザーを削除（204）。  
- `GET /api/v1/locations`：勤怠種別一覧を名前順で返す。  
- `POST /api/v1/locations` / `PUT /api/v1/locations/{location_id}`：勤怠種別の作成・更新。サービス層で重複/参照チェック。  
- `DELETE /api/v1/locations/{location_id}`：勤怠種別削除。CRUD側で利用中データの検証を実施。  
- `GET /api/v1/groups`：グループ一覧（order → name の順でソート）。  
- `POST /api/v1/groups` / `PUT /api/v1/groups/{group_id}` / `DELETE /api/v1/groups/{group_id}`：グループ CRUD。  
- `GET /api/v1/user_types`：社員種別一覧（order → name でソート）。  
- `POST /api/v1/user_types` / `PUT /api/v1/user_types/{user_type_id}` / `DELETE /api/v1/user_types/{user_type_id}`：社員種別 CRUD。  
- `GET /api/v1/csv/download?month=YYYY-MM&encoding=utf-8|sjis`：勤怠データをストリーミング出力。エンコーディング検証と月フォーマット検証を実施。Content-Disposition でファイル名を付与。

## UI 連携の留意点
- 勤怠 CRUD は HTMX モーダルから呼び出され、`HX-Trigger` (`closeModal` / `refreshUserAttendance` / `refreshAttendance`) を返す前提。UI の具体的なトリガー名は [UI 要件](../ui/requirements.md#カレンダーと勤怠登録) を参照。
- `/api/v1/csv/download` は `pages/csv.html` からクエリストリングを組み立ててダウンロードする。
- API が前提とするフィールド名や型は [DB 要件](../db/requirements.md) のモデル構成に従う。
