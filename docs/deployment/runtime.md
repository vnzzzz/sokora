# Production container runtime contract

sokora の production artifact は、閉域環境・GCP・AWS・Azureで共通利用する provider 非依存の OCI image とする。

## Artifact boundary

production imageに含めるもの:

- application code (`app/`)
- production Python dependencies（SQLite / PostgreSQL driver を含む）
- Alembic migration (`scripts/migration/`)
- fresh SQLite seedに必要な `scripts/seeding/data_seeder.py`
- build済み static assets / holiday cache
- container entrypoint

含めないもの:

- `.git`, `.github`, `.devcontainer`, agent設定
- docs / tests / test tooling
- Node.js / npm / uvなどのbuild tooling
- local SQLite DBやその他mutable local data
- cloud provider固有CLI / SDK / metadata service依存

## Runtime inputs

| Input | Contract |
| --- | --- |
| `PORT` | container内listen port。既定値 `8000`。managed container platformから上書き可能 |
| `DATABASE_URL` | DB接続先。既定値 `sqlite:///data/sokora.db`。SQLite / PostgreSQLを選択可能 |
| `SOKORA_*`, `OIDC_*` | application/auth設定。secretはimageへ埋め込まずruntime injectionする |
| proxy variables | 必要な環境だけ `HTTP_PROXY` / `HTTPS_PROXY` / lowercase variants / `NO_PROXY` 等をruntime injectionする |

local Make targetの `SERVICE_PORT` はhost側publish portであり、applicationのlisten contractとは分離する。

## Database backend

### SQLite

local/standalone/閉域で単一instanceから利用する場合の既定backend。`sqlite:///data/sokora.db` を利用し、container実行時は `/app/data` をpersistent volumeへ置く。

SQLite固有の `check_same_thread`、memory DB pool、foreign key PRAGMA はapplicationのDB runtime factoryに閉じ込め、他backendへ適用しない。

### PostgreSQL

managed container等からexternal PostgreSQLを利用できる。application contractは標準的な接続URLとする。

```text
postgresql://user:password@db.example:5432/sokora
postgresql://user:password@db.example:5432/sokora?sslmode=require
```

bare `postgresql://` / `postgres://` URL はproduction dependencyのPsycopg 3へ内部正規化する。provider名をURLやapplication codeへ追加する必要はない。明示的なSQLAlchemy PostgreSQL driver URLを指定した場合はその指定を維持する。

Cloud SQL for PostgreSQL、Amazon RDS/Aurora PostgreSQL、Azure Database for PostgreSQL等の差分はnetwork、DNS/socket、identity、TLS、secret injection等のdeployment adapterで吸収する。application/DB access層へprovider SDKやmetadata service依存を追加しない。

PostgreSQL backendの追加はDB接続・schema lifecycleをportableにするものであり、現時点のapplication全体についてhorizontal multi-replica consistencyを保証するものではない。calendar/holiday等にprocess-local cacheがあり、認証runtime stateにも別途整理対象があるため、後続deployment adapterはmulti-replica readinessが完了するまではapplication replicaを1に固定する。

## Persistent state / startup

DBやsecretをimage layerへ埋め込まない。SQLite利用時のみ `/app/data` をpersistent DB storageとして扱い、PostgreSQL利用時はcontainer filesystemをDB永続化に利用しない。

application startupはbackend共通で次のdatabase lifecycleを実行する。

1. Alembic migrationをheadまで適用する
2. fresh file-backed SQLiteの場合だけinitial seedを作成する
3. PostgreSQL / in-memory SQLiteでは自動seedしない
4. migration/seed失敗時はstartupをabortする

PostgreSQLでもfresh schemaは同じAlembic revision chainで構築する。schemaをbackend別に手管理しない。PostgreSQLのonline migrationはadvisory lockでsokoraのmigration session間を直列化し、同時startupや明示的なmigration commandが同じDDLを競合実行しないようにする。

## Health check

`GET /healthz` は認証不要で `200 {"status":"ok"}` を返す。OCI `HEALTHCHECK` と各deployment adapterのprobeはこのendpointを利用できる。

OCI healthcheckはPython標準ライブラリで `127.0.0.1:$PORT` へ直接接続し、runtimeのproxy環境変数を利用しない。proxy経由の外向き通信が必要な環境でもcontainer自身のhealth判定はproxy availabilityに依存しない。

## Build / proxy

production Dockerfileはrootの `Dockerfile` 1本だけを利用し、proxy有無でDockerfileやMake targetを分岐しない。

local Make contractは以下とする。

- `proxy` 未設定:
  - Makefileはproxy用build args / runtime environmentを追加しない。
  - Docker clientの `~/.docker/config.json` にproxyが設定されている場合は、Docker自身による自動proxy設定が別途適用され得る。
- `proxy` 設定あり:
  - build時は同じURLをDocker標準の `HTTP_PROXY` / `HTTPS_PROXY`（upper/lower case）build argsへ渡す。
  - runtime時は同じ値を `HTTP_PROXY` / `HTTPS_PROXY`（upper/lower case）環境変数へ渡す。
  - proxy値をDockerfileの `ENV` としてimageへ固定しない。
- `NO_PROXY` / `no_proxy`:
  - 指定値をbuild/runtime双方へupper/lower caseで渡す。
  - localhostのほか、proxyを経由させない社内OIDC/DB/API endpointがあればdeployment環境ごとに追加する。

sokoraのOIDC clientはHTTPXの通常clientを利用するため、runtimeで設定した標準proxy環境変数が外向きOIDC HTTP通信へ適用される。

provider固有のregistry、network、identity、secret service、probe設定等は後続deployment adapter側で定義し、production imageを変更しない。
