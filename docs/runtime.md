# Production container runtime contract

sokoraのproduction artifactは、deployment targetに依存しない共通OCI imageとする。この文書は**image/runtimeが満たすprovider非依存contract**のSSoTであり、providerごとの実装statusと入口は [Deployment guide](deployment.md) を参照する。共通imageとdeployment adapterを分離する判断理由は [ADR 0004](adr/0004-provider-neutral-oci-deployment.md) に記録する。

## Artifact boundary

production imageに含めるもの:

- application code (`app/`)
- production Python dependencies（SQLite / PostgreSQL driverを含む）
- Alembic migration (`scripts/migration/`)
- fresh SQLite seedに必要なseeding code
- build済みstatic assets / holiday cache
- container entrypoint

含めないもの:

- `.git`, `.github`, `.devcontainer`, agent設定
- docs / tests / test tooling
- Node.js / npm / uv等のbuild tooling
- local SQLite DBやその他mutable local data
- cloud provider固有CLI / SDK / metadata service依存

## Runtime inputs

| Input | Contract |
| --- | --- |
| `PORT` | container内listen port。既定`8000`。managed container platformから上書き可能 |
| `DATABASE_URL` | DB接続先。既定`sqlite:///data/sokora.db`。SQLite / PostgreSQLを選択 |
| `SOKORA_*`, `OIDC_*` | application/auth設定。secretはimageへ埋め込まずruntime injection |
| proxy variables | 必要な環境だけ`HTTP_PROXY` / `HTTPS_PROXY` / lowercase variants / `NO_PROXY`等をruntime injection |

local Make targetの`SERVICE_PORT`はhost側publish portであり、container listen contractとは分離する。

## Authentication runtime

認証設定はenvironment/secret injectionをSSoTとし、replica-local mutable fileを共有stateとして利用しない。

- `SOKORA_AUTH_ENABLED`の既定値は`false`。未設定のままではUI/APIのauthentication guardは無効で、signed sessionを要求しない。productionで認証を必要とする場合は明示的に`true`へ設定する。
- `SOKORA_AUTH_ENABLED=true`では、`SOKORA_AUTH_SESSION_SECRET`に空値や既定の`dev-session-secret`を利用できない。十分な強度の非default secretをruntime secretとして明示設定しない場合、startup validationは失敗する。
- OIDCは`OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` / `OIDC_REDIRECT_URL`等のruntime設定を利用する。
- Authlibがissuer discoveryからauthorization/token/JWKS/end-session metadataを取得し、provider固有endpoint pathをapplicationで組み立てない。
- sessionはStarlette `SessionMiddleware`のsigned client-side cookie。persistent sessionへOIDC access/refresh/ID tokenを保持しない。
- OAuth state / OIDC nonceはauthentication flow中だけsessionへ一時保持する。
- cookieはHttpOnly + SameSite=Lax。HTTPS productionでは`SOKORA_AUTH_SESSION_HTTPS_ONLY=true`を必須とする。
- multi-replicaでは`SOKORA_AUTH_SESSION_SECRET`と認証/OIDC設定を全replicaへ同一値で注入する。
- local admin loginは管理用fallbackで、自動failoverではない。
  - `SOKORA_LOCAL_AUTH_ENABLED`の既定値は`true`だが、このflagだけではlocal admin loginは有効にならない。
  - `SOKORA_LOCAL_AUTH_ENABLED=true` かつ `SOKORA_LOCAL_ADMIN_USERNAME` と `SOKORA_LOCAL_ADMIN_PASSWORD` の両方が設定されている場合だけlocal admin loginを有効化する。
  - credentialが不足している場合、applicationは起動できるがlocal admin loginは利用できない。`/auth/settings`、`/admin/database`等のadmin-only operationを利用するdeploymentでは、username/passwordをruntime secret/configとして明示設定する。

認証architectureの理由とsecurity boundaryは [ADR 0002](adr/0002-authentication-runtime.md)、HTTP guard behaviorは [API requirements](api.md) を参照する。

## Database backend

### SQLite

local/standalone/closedで単一instanceから利用する場合の既定backend。`sqlite:///data/sokora.db`を利用し、container実行時は`/app/data`をpersistent storageへ置く。

SQLite固有のconnection設定はDB runtimeへ閉じ込める。SQLiteはsingle-instance contractであり、複数application replicaから同じSQLite fileを共有する構成はsupportしない。

file-backed SQLiteのadmin backup/restoreは [SQLite database management](sqlite-database-management.md) を参照する。

### PostgreSQL

managed/external PostgreSQLを利用できる。application contractは標準PostgreSQL接続URLとする。

```text
postgresql://user:password@db.example:5432/sokora
postgresql://user:password@db.example:5432/sokora?sslmode=require
```

bare `postgresql://` / `postgres://`はproduction dependencyのPsycopg 3へ内部正規化する。Cloud SQL for PostgreSQL、Amazon RDS/Aurora PostgreSQL、Azure Database for PostgreSQL等の差分はdeployment adapter側のnetwork、identity、TLS、secret injection等で吸収し、application/DB access層へprovider SDKを追加しない。

### Horizontal multi-replica consistency

shared external PostgreSQLを全replicaで利用する場合、horizontal multi-replica runtimeをsupportする。詳細なconsistency contractは [ADR 0003](adr/0003-multi-replica-runtime.md) をSSoTとする。

application runtimeがreplica間共有stateとして依存してよいものは、shared DB、runtime-injected config/secret、同一imageに含まれるimmutable assetである。DB由来のmutable stateをmodule-global cacheやreplica-local fileへ共有stateとして保持しない。

## Persistent state and startup

DBやsecretをimage layerへ埋め込まない。SQLite利用時だけ`/app/data`をpersistent DB storageとして扱い、PostgreSQL利用時はcontainer filesystemをDB永続化に利用しない。

application startupはbackend共通で次を行う。

1. Alembic migrationをheadまで適用する。
2. fresh file-backed SQLiteの場合だけinitial seedを作成する。
3. PostgreSQL / in-memory SQLiteでは自動seedしない。
4. migration/seed失敗時はstartupをabortする。

PostgreSQLのonline migrationはadvisory lockでsokora migration process間を直列化する。schema lifecycleの詳細は [Database requirements](database.md) を参照する。

## Health check

`GET /healthz`は認証不要。

- DB runtimeが利用可能: `200 {"status":"ok"}`
- SQLite restore/recovery等でDB runtimeがfail-closedへfenceされた状態: `503 {"status":"unavailable"}`

health responseへ内部failure reasonやfilesystem pathを公開しない。OCI `HEALTHCHECK`はPython標準ライブラリで`127.0.0.1:$PORT`へ直接接続し、runtime proxy availabilityへ依存しない。

## Build and proxy

production Dockerfileはroot `Dockerfile` 1本を利用し、proxy有無でDockerfileやapplication codeを分岐しない。

local Make contract:

- `proxy`未設定: Makefileはproxy用build args/runtime envを追加しない。
- `proxy`設定あり: Docker標準の`HTTP_PROXY` / `HTTPS_PROXY`（upper/lower case）をbuild/runtimeへ渡す。proxy値をimage `ENV`へ固定しない。
- `NO_PROXY` / `no_proxy`: build/runtime双方へ渡し、localhostやproxy除外が必要なOIDC/DB endpointを環境ごとに追加する。

Docker client自身のproxy configurationが別途適用される場合があるため、Makefileの`proxy`設定とDocker daemon/client設定を混同しない。

## Deployment adapter boundary

provider adapterは、共通image/runtime contractを変更せず次を所有する。

- registry / image delivery
- service/container platform configuration
- network / ingress / TLS
- workload identity / secret injection
- external PostgreSQLへのprovider固有接続
- platform probe / scaling
- provider固有CLI、config、IaC

現時点でclosed-network adapterは実装済み。GCP/AWS/Azure adapterは #57 / #70 / #71 でplannedであり、未実装targetをdeploy support済みとは扱わない。statusと入口は [Deployment guide](deployment.md) を参照する。
