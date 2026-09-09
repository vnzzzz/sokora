# Sokora requirements

この文書は、sokora全体で現在成立させるcross-cutting contractを記載する。API、DB、UI、deployment、operationsの詳細は [Documentation guide](README.md) から各SSoTを参照する。

## Product scope

sokoraは、ユーザーの勤怠種別・勤務場所をカレンダーUIで可視化・編集するWeb applicationである。

主要な利用機能:

- 月次/週次カレンダーと日別詳細
- 勤怠の登録・更新・削除
- ユーザー、グループ、勤怠種別、社員種別、カスタム祝日の管理
- 月次勤怠CSVのダウンロード
- 月次/年度別の集計表示
- optionalなOIDC認証とlocal admin fallback
- file-backed SQLite利用時のadmin向けbackup/restore

## Architecture boundary

```text
HTTP adapters
├─ app/routers/pages/   -> HTML / HTMX
└─ app/routers/api/v1/ -> JSON API
          │
          ├─ write use cases -> app/services/ -> app/crud/
          └─ read paths      -> read service / app/crud/ / view helper
                                      │
                               app/models/ + app/db/
```

- JSON APIとpage/HTMX adapterはtransport contractを分離する。HTML fragmentや`HX-*` headerをJSON APIへ持ち込まない。
- write business ruleとtransaction coordinationはservice層へ集約し、page adapterからJSON APIへ内部HTTP委譲しない。
- read pathは画面/集計の複雑さに応じてdedicated read serviceまたは既存CRUD/read helperを利用する。DB由来のmutable stateをrouter/process-local cacheへ共有状態として保持しない。
- DB schema/data contractはSQLAlchemy modelとAlembicを基準にし、詳細は [Database requirements](database.md) をSSoTとする。
- UIの利用者向けbehaviorとHTMX contractは [UI requirements](ui.md) をSSoTとする。

## Database and state

- DB接続先のSSoTは`DATABASE_URL`とする。
- supported backendはSQLiteとPostgreSQL。
- SQLiteはlocal/standalone/closedのsingle-instance用途を対象とする。複数application replicaから同じSQLite fileを共有しない。
- horizontal multi-replica runtimeはshared external PostgreSQLを利用する。共有状態contractは [ADR 0003](adr/0003-multi-replica-runtime.md) に従う。
- schema lifecycleはSQLite/PostgreSQLともAlembicへ統一し、startup時にheadへ到達できなければserviceを開始しない。
- DB由来のmutable stateをreplica-local cache/fileへ共有状態として保持しない。

## Authentication and authorization

- authentication guardはruntime設定で有効化できる。
- 一般ユーザーの一次経路はprovider-neutralなOIDC Authorization Code flow。local loginは管理者専用fallbackであり、自動failoverは行わない。
- OIDC endpointはissuer discoveryから取得し、Keycloak等の特定provider固有pathをapplicationで組み立てない。
- sessionはStarletteのsigned client-side cookieとし、永続cookieへOIDC access/refresh/ID tokenを保持しない。
- HTTPS productionではSecure cookieを必須とし、全replicaへ同じsession signing secretと認証設定を注入する。
- admin-only routeは共通authorization dependencyで保護する。

認証architectureの採用理由は [ADR 0002](adr/0002-authentication-runtime.md)、HTTP/runtimeの詳細contractは [API requirements](api.md) と [Production runtime](runtime.md) を参照する。

## Production runtime and deployment

- production artifactはroot `Dockerfile`から生成するprovider非依存OCI image 1種類とする。
- containerは`PORT`でlistenし、DB/auth/config/secretはruntime injectionする。mutable DBやsecretをimageへ埋め込まない。
- image registry、container platform、network、ingress/TLS、identity、secret injection、managed PostgreSQL provisioning、probe、scaling、provider固有CLI/IaCはdeployment environment側の責務とする。
- application coreやDB access層へcloud provider固有SDKやprovider abstractionを追加しない。
- health checkは認証不要の`GET /healthz`を共通readiness入口とする。application runtimeが利用可能でDBへのlightweight queryが成功した場合だけ200を返し、maintenance/fence/DB unavailableでは503を返す。

共通runtime contractは [runtime.md](runtime.md)、generic container配置とSQLite/PostgreSQLの構成判断は [deployment.md](deployment.md)、architecture decisionは [ADR 0005](adr/0005-provider-neutral-deployment-contract.md) を参照する。

特定cloud provider向けのadapterやsupport statusは管理しない。閉域Docker deploymentだけは実装済みdistribution targetとして [closed-deployment.md](closed-deployment.md) にbundle/Compose/operator手順を維持する。

## Operations

- file-backed SQLiteでは`/admin/database`からadminがconsistent backupをdownloadし、current Alembic revision/schemaと互換なSQLite DBだけをrestoreできる。
- SQLite restoreはmigration手段ではない。古いrevisionのDBをrestoreしてstartup migrationへ暗黙に委ねない。
- PostgreSQL backup/restoreはDB運用基盤側の標準手段を利用し、application GUIでは扱わない。
- SQLite backup/restoreとfailure recoveryの詳細は [SQLite database management](sqlite-database-management.md) をSSoTとする。

## Documentation contract

- 現在成立させる仕様・利用条件はrequirements/runtime/operations文書へ記載する。
- architecture decisionの背景・trade-offはADRへ記録し、現在値や操作手順を重複させない。
- READMEとindexは入口として保ち、詳細仕様を複製しない。
- 実装済み事実、未実装事項、提案を混同しない。
