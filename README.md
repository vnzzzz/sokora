# sokora

![image](docs/images/image1.png)

直感的なカレンダー UI で勤怠（リモート / オフィス / 休暇など）を可視化・編集する Web アプリ。HTMX + Alpine.js で軽量に動き、FastAPI + SQLAlchemy で SQLite / PostgreSQL を利用できる。

## Features
- 月次/週次カレンダー、日別詳細、勤怠種別ごとの色分け表示
- HTMX モーダルによる勤怠 CRUD とマスタ管理（ユーザー / グループ / 勤怠種別 / 社員種別）
- CSV インポート/エクスポート、月次・年度別の集計ビュー
- 祝日キャッシュ表示とカスタム祝日管理（DB 保存で再ビルド後も保持）
- 任意で有効化できる認証ガード（標準OIDC + 管理者向けlocal login）

## Stack
- Backend: Python 3.13 / FastAPI / SQLAlchemy / Pydantic v2 / SQLite / PostgreSQL (Psycopg 3)
- Authentication: Authlib + OpenID Connect discovery / Starlette signed session
- Frontend: Jinja2 (SSR) + HTMX + Alpine.js + Tailwind CSS (daisyUI)
- Tooling: uv, pytest + pytest-playwright, Ruff, mypy, Tailwind ビルド用 Node
- Runtime: provider非依存のproduction OCI image。container listen portは `PORT`（既定 `8000`）。

## Quick Start（ローカル/Dev Container）
1) `.env.sample` をコピーして `.env` を用意し、少なくとも `VERSION`（任意のタグ）と `SERVICE_PORT` を埋める  
2) 依存と開発用アセットを準備:  
```bash
make install   # uv sync --locked + builder npm ci + assets/ と祝日キャッシュを生成
```
3) アプリ起動（ホットリロード）:  
```bash
make run       # http://localhost:${SERVICE_PORT}
```
   - Makefile は `VERSION` 未設定だとエラー。`.env` に必ず設定する。
   - DB接続先は `DATABASE_URL` で指定する。既定値は `sqlite:///data/sokora.db`。
   - PostgreSQLは `postgresql://user:password@host:5432/database` 形式をそのまま指定できる。bare PostgreSQL URLはproduction dependencyのPsycopg 3へ内部正規化する。
   - 起動時に SQLite / PostgreSQL とも Alembic migration を head まで適用する。file-backed SQLite DBが新規作成された場合だけシーディング（60日/60日分）も実施し、PostgreSQLは自動seedしない。
4) 停止: `make docker-stop`（コンテナ実行時）またはサーバープロセスを終了

Python依存関係は `pyproject.toml` と `uv.lock` で管理する。既存lockを変更せず再現する場合は `uv sync --locked` を使用する。

DB migrationだけを明示実行する場合は `make migrate`（`alembic upgrade head`）を使用する。schema lifecycleとbackend contractの詳細は [docs/db/requirements.md](docs/db/requirements.md) を参照。

静的スタイルを触る場合は `builder/input.css` を編集し、`make assets` で `assets/` を再生成（ビルド成果物は直接編集しない）。

## Python quality

Pythonのlint・import sorting・formatはRuff、型検査はmypyに統一している。ローカルとCIは同じMake targetを利用する。

```bash
make lint          # Ruff lint + import sorting check
make format        # Ruffでimport sortingとformatを適用
make format-check  # format差分がないことだけ確認
make typecheck     # mypy
make quality       # lint + format-check + typecheck
```

PR前の標準的な静的検証は `make quality`。CIも同じtargetを実行する。

## Database

`DATABASE_URL` がDB接続のSSoTで、application startupと `make migrate` は同じAlembic revision chainを利用する。

SQLite（既定）:

```text
DATABASE_URL=sqlite:///data/sokora.db
```

PostgreSQL:

```text
DATABASE_URL=postgresql://sokora:password@db.example:5432/sokora
DATABASE_URL=postgresql://sokora:password@db.example:5432/sokora?sslmode=require
```

- SQLite固有のconnection設定・FK PRAGMAはDB runtime factoryへ閉じ込め、PostgreSQLへ適用しない。
- PostgreSQL driverはPsycopg 3。`postgresql://` / `postgres://` は内部で `postgresql+psycopg` へ正規化する。
- Cloud SQL for PostgreSQL / Amazon RDS・Aurora PostgreSQL / Azure Database for PostgreSQLもapplication側では標準PostgreSQL接続情報として扱う。provider固有SDKはapplication/DB access層へ追加しない。
- PostgreSQLではcontainer filesystemをDB永続化に利用せず、startup時の自動seedも行わない。

## Docker

production imageはrootの `Dockerfile` 1本だけでbuildする。Node/uv/test/docs/agent設定はbuild/runtime artifactへ残さず、同じOCI imageを閉域/GCP/AWS/Azureのdeployment adapterから利用する。

- プロダクションビルド: `make docker-build`（タグは `.env` の `VERSION`）
- 実行: `make docker-run`
  - host側 `SERVICE_PORT` をcontainer側 `PORT`（既定 `8000`）へpublish
  - SQLite利用時は `data/` を `/app/data` へvolume mount
- `DATABASE_URL` はapplication runtimeのSSoT。schema migrationはapplication startupでAlembic headまで適用する。
- fresh file-backed SQLiteはstartup時だけseedする。DBをimage layerへ埋め込まない。
- health check: `GET /healthz`（認証不要）

### Proxy

proxy有無でDockerfileやMake targetは分岐しない。常に `make docker-build` / `make docker-run` を利用する。

- `proxy` 未設定: Makefileからproxy build args / runtime proxy環境変数は追加しない。
- `proxy=http://proxy.example:8080` 設定時:
  - buildではDocker標準の `HTTP_PROXY` / `HTTPS_PROXY`（upper/lower case）build argsとして渡す。
  - runtimeでは同じ値を `HTTP_PROXY` / `HTTPS_PROXY`（upper/lower case）としてcontainerへ注入する。
  - build時に利用したproxy値はproduction imageへ `ENV` として固定しない。
- `NO_PROXY`（または `no_proxy`）を指定するとbuild/runtime双方へupper/lower caseで渡す。localhostに加え、proxyを経由させない社内OIDC/DB等があれば追加する。
- OCI healthcheckは `127.0.0.1` へPython標準ライブラリで直接接続するため、runtime proxy設定に依存しない。

Docker client側の `~/.docker/config.json` にproxyが設定されている場合は、`proxy` 未設定でもDocker自身がbuild/containerへproxy設定を自動注入する場合がある。Makefileの `proxy` はlocal `.env` から明示的にproxyを与えるための入口である。

詳細なproduction runtime contractは [docs/deployment/runtime.md](docs/deployment/runtime.md) を参照。

## Authentication
- defaultは `SOKORA_AUTH_ENABLED=false` でguard無効。trueにするとUI/API双方でsigned sessionを要求する。
- OIDCは `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URL` が揃うと有効。Authlibがissuer discoveryを使うため、Keycloak固有endpointをapplication側で設定しない。
- authorization flowのstate/nonceとID token validationはAuthlibへ委譲する。認証後cookieへ保存するのはmethod/subject/username等の最小identityだけで、access/refresh/ID tokenは保存しない。
- local admin loginは `SOKORA_LOCAL_AUTH_ENABLED=true` かつusername/passwordが揃うと有効。SSO障害時の管理用fallbackであり、自動failoverはしない。
- 認証設定はruntime environment/secretをSSoTとし、replica-local fileによるruntime toggleは持たない。`/auth/settings` はadmin向けread-only diagnostics。
- session cookieはHttpOnly + SameSite=Lax。HTTPS productionでは `SOKORA_AUTH_SESSION_HTTPS_ONLY=true` を必須とする。`SOKORA_AUTH_SESSION_SECRET` はproduction secretへ差し替える。

## Environment Variables
| Name | Default | Description | Example |
| --- | --- | --- | --- |
| SERVICE_PORT | 8000 | local Docker/devで利用するhost側公開ポート | 8000 |
| PORT | 8000 | production container内のHTTP listen port | 8080 |
| VERSION | なし (必須) | Docker イメージタグ（Makefile が必須扱い） | 1.0.0 |
| proxy | なし | local build/run用proxy URL。Dockerfile自体は分岐しない | http://proxy.local:8080 |
| NO_PROXY | localhost,127.0.0.1 | proxy除外先。必要に応じて社内endpointを追加 | localhost,127.0.0.1,idp.internal |
| SOKORA_LOG_LEVEL | INFO | ログレベル | DEBUG |
| DATABASE_URL | sqlite:///data/sokora.db | SQLite/PostgreSQLのSQLAlchemy DB接続URL | postgresql://sokora:secret@db.example:5432/sokora?sslmode=require |
| SOKORA_AUTH_ENABLED | false | 認証ガードの有効/無効 | true |
| SOKORA_AUTH_SESSION_SECRET | dev-session-secret | signed session cookieの署名キー。productionではsecret injection必須 | change-me-prod-secret |
| SOKORA_AUTH_SESSION_TTL_SECONDS | 3600 | session cookie有効期限（秒） | 7200 |
| SOKORA_AUTH_SESSION_HTTPS_ONLY | false | session cookieへSecure属性を付与。HTTPS productionではtrue必須 | true |
| SOKORA_LOCAL_AUTH_ENABLED | true | local admin認証の有効/無効 | false |
| SOKORA_LOCAL_ADMIN_USERNAME | なし | local admin username | admin |
| SOKORA_LOCAL_ADMIN_PASSWORD | なし | local admin password | strong-password |
| OIDC_ISSUER | なし | OpenID Provider issuer | https://idp.example.com/realms/sokora |
| OIDC_CLIENT_ID | なし | OIDC client ID | sokora-web |
| OIDC_CLIENT_SECRET | なし | OIDC client secret | super-secret |
| OIDC_REDIRECT_URL | なし | registered authorization callback URL | https://sokora.example.com/auth/callback |
| OIDC_SCOPES | openid profile email | 要求scope | openid profile email |
| OIDC_HTTP_TIMEOUT | 3.0 | OIDC discovery/token通信のtimeout秒 | 5.0 |
| SEED_DAYS_BACK | 60 | シードする過去日の日数 | 30 |
| SEED_DAYS_FORWARD | 60 | シードする未来日の日数 | 30 |

## Tests
```bash
make test
```
`scripts/testing/run_test.sh` が DB クリーンアップ → API/ユニット → E2E を順に実行し、サーバーが無ければ自動起動する（テスト中は `SOKORA_AUTH_ENABLED=false` を強制）。

CIはSQLiteの通常quality/non-E2E/E2E、real PostgreSQLを使ったmigration/startup/主要CRUD integration test、production imageのproxyなし/ありbuild・runtime、`PORT` override、`/healthz`、development-only資産/ツールの不在を検証する。

## Project Layout
- `app/main.py` / `app/routers/`: API v1 と各ページルーター（auth/calendar/attendance/analysis など）
- `app/templates/`: `layout/base.html` ベースのページ・コンポーネント。HTMX/Alpine.js 用の部分テンプレートは `components/partials/`。
- `app/static/`: 開発用 JS/CSS。`assets/` は Tailwind ビルド成果物。
- `builder/`: Tailwind + daisyUI のビルドソース、`scripts/`: アセット・シーディング・マイグレーション・テスト補助
- `docs/`: [requirements.md](docs/requirements.md) から API/DB/UI/runtime仕様へリンク
