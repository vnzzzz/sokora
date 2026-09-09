# Runtime

production artifactはroot `Dockerfile`からbuildするprovider-neutral OCI image 1種類です。配置方法は [Deployment](deployment.md) を参照してください。

## Image boundary

| Inside image | Outside image |
| --- | --- |
| application code | SQLite / PostgreSQL data |
| production Python dependencies | runtime secret / credential |
| Alembic migration | environment-specific config |
| fresh SQLite seed code | provider CLI / IaC |
| built static assets / holiday asset | docs / tests / dev tooling |
| container entrypoint | build cache / local source state |

mutable DBやsecretをimage layerへ埋め込みません。

## Runtime inputs

| Input | Purpose |
| --- | --- |
| `PORT` | container listen port。既定8000 |
| `DATABASE_URL` | SQLite / PostgreSQL接続先 |
| `SOKORA_LOG_LEVEL` | application log level |
| `SOKORA_AUTH_*`, `OIDC_*` | authentication / OIDC設定 |
| `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`等 | 必要な環境だけproxyを注入 |

local Make targetの`SERVICE_PORT`はhost publish portで、container内部の`PORT`とは別です。

root `.env` はlocal Make workflowとapplication runtimeの入力を同じfileで管理しますが、責務は分かれています。

| Scope | Variables |
| --- | --- |
| Make workflow only | `SERVICE_PORT`, `VERSION`, `proxy` |
| Container/application runtime | `PORT`, `DATABASE_URL`, `SOKORA_*`, `OIDC_*` |
| Proxy runtime/build | `proxy`から展開するHTTP(S) proxy、`NO_PROXY` / `no_proxy` |

`make docker-run` はroot `.env` を `--env-file` で丸ごとcontainerへ渡しません。既知のapplication runtime変数だけを明示的にforwardし、`VERSION`や`SERVICE_PORT`などMake専用値をcontainer environmentへ混入させません。

authentication settingの意味とprecedenceは [Authentication](authentication.md)、DB URLは [Database](database.md) を参照してください。

## Startup

```mermaid
flowchart TD
    Start["Container start"] --> Settings["Validate runtime settings"]
    Settings --> DB["Initialize DB runtime"]
    DB --> Migration["Alembic upgrade head"]
    Migration --> Backend{"Fresh file-backed SQLite?"}
    Backend -->|yes| Seed["Initial seed"]
    Backend -->|no| Ready["Accept traffic"]
    Seed --> Ready

    Settings -->|failure| Abort["Startup abort"]
    DB -->|failure| Abort
    Migration -->|failure| Abort
    Seed -->|failure| Abort
```

production schemaを`Base.metadata.create_all()`で作成しません。

## Health

`GET /healthz`は認証不要のreadiness endpointです。

| Status | Meaning |
| --- | --- |
| `200 {"status":"ok"}` | DB runtimeがrequest処理可能で、`alembic_version`へのreadiness queryが成功する |
| `503 {"status":"unavailable"}` | runtime未初期化、maintenance/fenced、DB unavailable、readiness query failure |

`/healthz`はAlembic revisionがapplicationのcurrent headと一致することまでは検証しません。schema migrationはstartupで`alembic upgrade head`を完了させる前提です。

health responseへexception、credential、filesystem pathを露出しません。

OCI `HEALTHCHECK`はcontainer内の`127.0.0.1:$PORT`へ直接接続し、runtime proxy availabilityに依存しません。pure process liveness用`/livez`は提供していません。

## Multi-replica

multi-replicaは全instanceが同じexternal PostgreSQLとruntime secret/configを共有する構成です。DB由来mutable stateをreplica-local cache/fileへ共有状態として持ちません。

詳細は [Architecture](architecture.md) と [ADR 0003](adr/0003-multi-replica-runtime.md) を参照してください。

## Build and proxy

production Dockerfileはproxy有無で分岐しません。

- `proxy`未設定: Makefileはproxy build arg / runtime envを追加しない
- `proxy`設定あり: Docker標準のupper/lowercase proxy variablesをbuild/runtimeへ渡す
- `NO_PROXY` / `no_proxy`: DB / OIDC / localhost等、proxy除外先を環境ごとに設定

proxy valueをimage `ENV`へ固定しません。Docker daemon/client側のproxy設定はMakefileの`proxy`変数とは別の責務です。

## Environment responsibility

registry、container platform、network、ingress/TLS、identity、secret store、external PostgreSQL provisioning、platform scalingはdeployment environment側で構成します。

特定cloud provider向けSDKやdeployment abstractionをapplication coreへ追加しません。
