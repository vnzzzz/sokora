# Deployment

sokoraは同じproduction OCI imageを一般的なcontainer runtimeで実行します。特定cloud provider向けadapter / IaC / support matrixはrepositoryで管理しません。

## Topology

```mermaid
flowchart LR
    Image["sokora OCI image"]

    Image --> Single["Single container"]
    Single --> Volume["Durable filesystem<br/>/app/data"]
    Volume --> SQLite[("SQLite")]

    Image --> Replicas["1..N containers"]
    Replicas --> PostgreSQL[("External / managed PostgreSQL")]
```

## Runtime requirements

container environmentには次が必要です。

| Requirement | Contract |
| --- | --- |
| image | OCI imageを実行できる |
| network | containerが`0.0.0.0:$PORT`でlistenできる |
| config | environment / secret injection |
| database | selected DBへ到達できる |
| readiness | `GET /healthz`をprobeできる |
| public access | 必要ならHTTPS ingress / TLSをruntime側で終端 |

registry、VPC/VNet、load balancer、TLS certificate、secret store、managed DBそのもののprovisioningはsokoraの責務外です。

## Choose a database

| | SQLite | PostgreSQL |
| --- | --- | --- |
| application replica | 1 | 1..N |
| persistent state | `/app/data` filesystem | DB service |
| suitable for | standalone / small closed runtime | managed DB / multi-replica |
| backup | sokora SQLite backup / operator backup | DB platform |
| `DATABASE_URL` | `sqlite:///data/sokora.db` | standard PostgreSQL URL |

### SQLite

1. file locking / atomic write等のSQLite semanticsを満たすdurable filesystemを`/app/data`へmount
2. application replicaを1つに固定
3. `DATABASE_URL=sqlite:///data/sokora.db`を設定
4. startup後に`/healthz`を確認
5. backup / restoreは [SQLite database management](sqlite-database-management.md) に従う

containerのephemeral filesystemやobject storage bucketをSQLite DB fileの直接配置先にしません。適切なfilesystemを提供できないruntimeではPostgreSQLを選択します。

### External / managed PostgreSQL

providerに関係なく、applicationからはstandard PostgreSQLとして扱います。

1. PostgreSQL databaseとapplication credentialを用意
2. containerからDB endpointへのnetwork pathを構成
3. 必要ならTLS optionを接続URLへ設定
4. `DATABASE_URL`をruntime secretとして注入
5. containerを起動
6. startup migrationと`/healthz`を確認
7. backup / restoreはDB platform側で構成

```text
DATABASE_URL=postgresql://user:password@db.example:5432/sokora?sslmode=require
```

multi-replicaでは全replicaが同じDBとruntime secret/configを利用します。

## Startup

schema lifecycleはapplication startupが所有します。Alembic migrationがheadまで到達しない場合、applicationはtrafficを受けません。

runtime詳細は [Runtime](runtime.md)、schema詳細は [Database](database.md) を参照してください。

## Closed network

閉域Dockerサーバー向けにはrepository-owned bundle / Compose / operator workflowを用意しています。

```bash
VERSION=<version> make closed-bundle
```

搬入、image検証、persistent config、SQLite/PostgreSQL選択、upgrade/rollbackは [Closed-network deployment](closed-deployment.md) を参照してください。
