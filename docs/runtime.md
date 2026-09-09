# Production container runtime contract

sokoraのproduction artifactは、deployment targetに依存しない共通OCI imageとする。この文書は**image/runtimeが満たすprovider非依存contract**のSSoTである。一般的なcontainer環境への配置条件とDB構成は [Deployment guide](deployment.md)、provider別adapterを持たない現在の判断は [ADR 0005](adr/0005-provider-neutral-deployment-contract.md) を参照する。

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

session signing、authentication guard、local admin credentialはdeployment runtime secret/configをSSoTとする。OIDC client設定はshared DBへ移行可能で、replica-local mutable fileは利用しない。

- `SOKORA_AUTH_ENABLED`の既定値は`false`。productionで認証を必要とする場合は明示的に`true`へ設定する。
- `SOKORA_AUTH_ENABLED=true`では、`SOKORA_AUTH_SESSION_SECRET`に空値や既定の`dev-session-secret`を利用できない。
- local adminはbreak-glass管理経路としてruntime設定を維持する。
  - `SOKORA_LOCAL_AUTH_ENABLED=true`かつ`SOKORA_LOCAL_ADMIN_USERNAME` / `SOKORA_LOCAL_ADMIN_PASSWORD`が揃う場合だけ有効。
  - OIDCのDB設定、暗号鍵、discoveryに問題があってもlocal admin login自体はDB-backed OIDC resolverへ依存しない。
- OIDC設定sourceは次の3状態。
  1. `auth_config` rowなし: 既存deploymentとの互換性のため`OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` / `OIDC_SCOPES`をlegacy sourceとして利用する。
  2. `auth_config` rowあり + enabled: issuer / client ID / encrypted client secret / scopeはshared DBをSSoTとする。
  3. `auth_config` rowあり + disabled: OIDCを明示無効化し、legacy environmentへfallbackしない。
- `OIDC_REDIRECT_URL`と`OIDC_HTTP_TIMEOUT`はdeployment/runtime propertyとしてenvironmentに残す。
- DB-backed client secretはFernetで暗号化し、暗号鍵`SOKORA_AUTH_CONFIG_ENCRYPTION_KEY`はDB/imageへ保存せずruntime secretとして全replicaへ同一値を注入する。鍵は`python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`等で生成できる。
- DB-backed OIDCを有効化する場合、暗号鍵未設定・不正・不一致はOIDCを利用不可とし、legacy secretへfallbackしない。
- `/auth/settings`はlocal adminだけが利用できる。OIDC設定の保存・明示無効化・連携解除・standard discovery接続確認を提供する。これらのPOSTはsession-backed CSRF tokenを必須とする。OIDCをenabledで保存する場合は`openid` scope、discovery取得、metadata issuerの末尾slashを含むexact一致を必須検証し、失敗時は有効設定をDBへ保存しない。保存済みclient secretは画面へ再表示しない。
- application logoutはprovider logoutより優先する。`POST /auth/logout`はshared DB / IdPへアクセスせず、最初のresponseでauthenticated identityをsession cookieから除去する。OIDC sessionの場合だけ、その後の別requestでprovider logoutをbest-effort実行するため、DB接続black-holeやshared DB unavailableでもlocal logout完了をblockしない。
- Authlibがissuerの`/.well-known/openid-configuration`からauthorization/token/JWKS/end-session metadataを取得し、Keycloak固有endpointをapplicationで組み立てない。
- sessionはStarlette `SessionMiddleware`のsigned client-side cookie。persistent sessionへOIDC access/refresh/ID tokenを保持しない。
- OAuth state / OIDC nonceはauthentication flow中だけsessionへ一時保持する。
- cookieはHttpOnly + SameSite=Lax。HTTPS productionでは`SOKORA_AUTH_SESSION_HTTPS_ONLY=true`を必須とする。
- multi-replicaではshared PostgreSQLの`auth_config`をrequest時に参照し、process-local OIDC settings cacheを共有stateとして持たない。OIDC redirect/callback用の設定読取はshort-lived DB session内で完了・closeしてからIdP HTTP処理へ進む。管理画面でenabled設定を保存する場合もDiscoveryをDB session取得前に完了させる。いずれも外部I/O待ち中にchecked-out DB connectionを保持しない。

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

bare `postgresql://` / `postgres://`はproduction dependencyのPsycopg 3へ内部正規化する。external / managed PostgreSQLもapplicationからは標準PostgreSQL接続として扱う。network、TLS、credential/secret injection等はdeployment environment側で構成し、application/DB access層へprovider固有SDKやDB proxy processを追加しない。

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

`GET /healthz`は認証不要のreadiness probe。

`200 {"status":"ok"}` を返す条件:

- application-scoped DB runtimeが初期化済み
- SQLite restore等のexclusive maintenance中ではない
- DB runtimeがfail-closedへfenceされていない
- file-backed SQLiteではread-only connectionで実Alembic schemaを確認できる
- PostgreSQLではrequest poolと独立した短時間接続で実Alembic schemaを確認できる
- in-memory SQLiteではapplicationが実際に利用するruntime engine上でAlembic schemaを確認できる

上記を満たさない場合は `503 {"status":"unavailable"}` を返す。file-backed SQLiteはread-only connectionでAlembic schemaを読み、missing/empty/schema-loss時にDBを新規作成せずunavailableとする。PostgreSQLはrequest poolと分離した短時間connectionでAlembic schemaを読み、connect / statement timeoutを持つ。in-memory SQLiteは別connectionでは別DBになるため、application runtime engine自身のAlembic schemaへread queryを行う。health responseへ内部exception、credential、filesystem path等を公開しない。

OCI `HEALTHCHECK`はPython標準ライブラリで`127.0.0.1:$PORT`へ直接接続し、runtime proxy availabilityへ依存しない。純粋なprocess liveness用`/livez`は現時点では提供しない。

## Build and proxy

production Dockerfileはroot `Dockerfile` 1本を利用し、proxy有無でDockerfileやapplication codeを分岐しない。

local Make contract:

- `proxy`未設定: Makefileはproxy用build args/runtime envを追加しない。
- `proxy`設定あり: Docker標準の`HTTP_PROXY` / `HTTPS_PROXY`（upper/lower case）をbuild/runtimeへ渡す。proxy値をimage `ENV`へ固定しない。
- `NO_PROXY` / `no_proxy`: build/runtime双方へ渡し、localhostやproxy除外が必要なOIDC/DB endpointを環境ごとに追加する。

Docker client自身のproxy configurationが別途適用される場合があるため、Makefileの`proxy`設定とDocker daemon/client設定を混同しない。

## Deployment environment boundary

sokora repositoryが所有するのは、共通image/runtime contractと、SQLite / PostgreSQLのapplication-level contractまでとする。

deployment environment側で構成するもの:

- image registry / image delivery
- service/container platform configuration
- network / ingress / TLS
- workload identity / secret injection
- external / managed PostgreSQLのprovisioningと接続network
- platform probe / scaling
- provider固有CLI、config、IaC

特定cloud provider向けのadapter、deploy script、IaC、support matrixはrepositoryで提供しない。一般的な配置条件は [Deployment guide](deployment.md) を参照する。

closed-network Docker deploymentは実装済みのdistribution targetとして例外的にrepository-owned assetsを持つ。bundle、Compose、operator手順、upgrade/rollback、validationは [Closed-network deployment](closed-deployment.md) を参照する。
