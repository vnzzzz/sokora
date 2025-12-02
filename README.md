# sokora

![image](docs/images/image1.png)

直感的なカレンダー UI で勤怠（リモート / オフィス / 休暇など）を可視化・編集する Web アプリケーションです。HTMX + Alpine.js で軽量なインタラクションを実現し、FastAPI + SQLite でシンプルに運用できます。

## 主な機能
- カレンダー表示: 月次ビュー、日別詳細、勤怠種別ごとの色分け表示
- 勤怠登録・編集: HTMX モーダルで高速入力、月・週の選択状態を保存
- マスタ管理: ユーザー / グループ / 勤怠種別 / 社員種別の CRUD
- CSV 入出力: 勤怠データのエクスポート / インポート
- 集計: `/analysis` で月次・年度別の勤怠集計、種別別の詳細ビュー
- 祝日表示: ビルド時に取得した祝日キャッシュを表示・判定に利用
- 祝日管理: 画面から追加・編集・削除した祝日はDBに保存され、再ビルド後も維持されます

## 技術スタック
- Backend: Python 3.13, FastAPI, SQLAlchemy, Pydantic v2, SQLite
- Frontend: Jinja2 (SSR), HTMX, Alpine.js, Tailwind CSS + daisyUI
- Build: Poetry, Tailwind ビルド用 Node（Docker multi-stage）
- Infra: Docker / docker-compose（ポートは `SERVICE_PORT` 環境変数で指定）

## ドキュメント
- 要件集約: `docs/requirements.md`（API/DB/UI へのリンク付き）
- API 要件: `docs/api/requirements.md`
- DB 要件: `docs/db/requirements.md`
- UI 要件: `docs/ui/requirements.md`
- テンプレート構成: `docs/ui/templates.md`

## ディレクトリ概要
- `app/main.py`: FastAPI エントリーポイント（静的/ビルド資産のマウント、ルーター登録）
- `app/routers/api/v1/`: JSON API（勤怠・ユーザー・グループ・種別・CSV）
- `app/routers/pages/`: HTML/HTMX ページ（top, calendar, attendance, register, analysis など）
- `app/templates/`: レイアウト/コンポーネント/ページテンプレート
- `app/static/`: 開発用 JS/CSS（`calendar.js`, `modal.js`, `analysis.js` など）
- `assets/`: ビルド成果物（`assets/css/main.css`, `assets/js/htmx.min.js` 等）。`static/` は手書きの開発用スクリプト、`assets/` はビルドした配布物という役割分担。
- `builder/`: Tailwind + daisyUI 設定とビルドソース（`input.css`）
- `scripts/`: 祝日キャッシュ取得、シーディング、マイグレーション、テストスクリプト
- `data/`: 本番/開発用 SQLite DB (`sokora.db`)

## セットアップ（Docker / Makefile）
1. `.env.sample` を参考に `.env` を作成し、`SERVICE_PORT` を設定します。
2. ビルドと起動:
   ```bash
   make build      # プロダクションイメージをビルド（DBが無ければビルド時に初期化・シード）
   make run        # SERVICE_PORT で uvicorn を起動（devcontainer でも同様）
   ```
   - `data/sokora.db` が存在しない場合は、`make run` / `make docker-run` の起動時にテーブル作成とシーディング（60日/60日分）を自動実行します。Docker ビルド済みイメージにはシード済み DB が `/app/seed/sokora.db` として同梱され、`make docker-run` でホストマウントされた `data/` が空ならエントリポイントがコピーします。
   - プロキシ経由でビルド/起動する場合は `.env` の `proxy` に URL を設定し、`make docker-build-proxy` / `make docker-run-proxy` を使用してください。
3. アクセス: `http://localhost:${SERVICE_PORT}`
4. 停止: `make stop`

初回セットアップは `make install` で Python / npm 依存とアセットをまとめて準備できます。`make run`・`make test` などのターゲット実行時も、依存が未インストールなら自動で `poetry install` を走らせます。

## 環境変数
| 変数名 | デフォルト | 説明 |
| --- | --- | --- |
| SERVICE_PORT | 8000 | アプリケーションの公開ポート（`make run` / `make docker-run` が参照） |
| VERSION | なし（必須） | Docker イメージタグに使用（`make docker-build` / `make docker-run`） |
| proxy | なし | プロキシ経由で Docker ビルド/実行する際の proxy URL（`make docker-build-proxy` / `make docker-run-proxy`） |
| SOKORA_LOG_LEVEL | INFO | ログレベル（DEBUG/INFO/WARN/ERROR） |
| SOKORA_AUTH_ENABLED | false | 認証ガードの有効/無効 |
| SOKORA_AUTH_SESSION_SECRET | dev-session-secret | セッションクッキー署名用シークレット（本番は必ず上書き） |
| SOKORA_AUTH_SESSION_TTL_SECONDS | 3600 | セッション有効期限（秒） |
| SOKORA_LOCAL_AUTH_ENABLED | true | ローカル管理者認証の有効/無効 |
| SOKORA_LOCAL_ADMIN_USERNAME | なし | ローカル管理者ユーザー名（設定時のみローカル認証が有効） |
| SOKORA_LOCAL_ADMIN_PASSWORD | なし | ローカル管理者パスワード |
| SOKORA_AUTH_STATE_PATH | data/auth_state.json | OIDC 有効/無効状態を保持するストレージパス |
| OIDC_ISSUER | なし | OIDC IdP の issuer URL（設定時に OIDC を利用） |
| OIDC_CLIENT_ID | なし | OIDC クライアント ID |
| OIDC_CLIENT_SECRET | なし | OIDC クライアントシークレット |
| OIDC_REDIRECT_URL | なし | OIDC リダイレクト先 URL（例: `http://localhost:${SERVICE_PORT}/auth/callback`） |
| OIDC_SCOPES | openid profile email | 要求する OIDC スコープ |
| OIDC_HTTP_TIMEOUT | 3.0 | OIDC リクエストのタイムアウト秒 |
| OIDC_AUTHORIZATION_ENDPOINT | なし | Authorization Endpoint の上書き（省略時は discovery 依存） |
| OIDC_TOKEN_ENDPOINT | なし | Token Endpoint の上書き |
| OIDC_USERINFO_ENDPOINT | なし | UserInfo Endpoint の上書き |
| OIDC_LOGOUT_ENDPOINT | なし | ログアウト用 Endpoint の上書き |
| SEED_DAYS_BACK | 60 | `make seed` の過去分シード日数 |
| SEED_DAYS_FORWARD | 60 | `make seed` の未来分シード日数 |

- `SOKORA_AUTH_SESSION_TTL_SECONDS` と `SOKORA_AUTH_STATE_PATH` はアプリにデフォルトがあるため `.env.sample` には含めていません。カスタムしたい場合のみ `.env` に追記してください。
- `SOKORA_AUTH_SESSION_SECRET` は本番環境で必ず安全な値に置き換えてください。

### 開発用コンテナ（devcontainer と共通）
- イメージビルド: `make dev-build`
- サーバ起動（ホットリロード）: `make run`
- シェルで作業: `make dev-shell`
- 本番コンテナ実行前に `make docker-build`（DBが無い場合はビルド時に初期化・シード）→ `make docker-run`（ホストの `data/` をバインド）

> 備考: Docker ビルド時に Tailwind ビルドと祝日キャッシュ取得を実行し、`assets/` に成果物を配置します。ビルド生成物を直接編集しないでください。必要な場合は `make assets` で再生成します。
> devcontainer 起動直後は Web サーバーを立ち上げずポートもフォワードしません。`make run` を実行したときに `.env` の `SERVICE_PORT` でホスト側へバインドされます。

## ローカル開発（非コンテナ）
```bash
# 依存関係
poetry install

# アプリ起動（ホットリロード）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- 静的スタイルを変更する場合は `builder/input.css` を編集し、`make assets`（内部で `scripts/build_assets.sh` を実行）で CSS/JS を再生成してください（Docker ビルドでは自動生成）。

## テスト
総合テストスクリプト（DB クリーンアップ込み）:
```bash
make test
```
- API/ユニットテストは in-memory SQLite を利用します。
- E2E テスト（Playwright）は `http://localhost:8000` へのアクセスが前提なので、`make dev-up` などでアプリを起動してから実行してください。

## シーディング・ユーティリティ
- 勤怠ダミーデータ投入: `make seed` （既存ユーザー・勤怠種別が前提）
- 祝日キャッシュ生成（ビルド時と同等）: `python3 scripts/build_holiday_cache.py`  
  生成物は `assets/json/holidays_cache.json` に保存され、`app/utils/holiday_cache.py` から読み込まれます。

## 開発ポリシー（概要）
- 既存レイヤー（ルーター → サービス → CRUD → モデル）とテンプレート構造を踏襲する。
- スキーマ/API/UI の変更は対応するテストを更新する。
- **TDD を徹底**（落ちるテストを先に書き、最小実装で緑にしてからリファクタ）。
- Dockerfile / docker-compose の大規模変更や外部依存追加は事前合意の上で行う。
