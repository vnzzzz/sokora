# Deployment guide

sokoraのproduction artifactは、root `Dockerfile`から生成するprovider非依存OCI image 1種類とする。

この文書は、特定cloud providerのdeploy手順やsupport statusではなく、一般的なcontainer runtimeへsokoraを配置するときに必要な共通条件と、SQLite / external PostgreSQLの構成判断を記載する。runtime内部の詳細contractは [runtime.md](runtime.md)、architecture decisionは [ADR 0005](adr/0005-provider-neutral-deployment-contract.md) を参照する。

実装済みの閉域Dockerサーバー向けdeploymentは、bundle生成、Compose、upgrade/rollback、proxy、validationまで [closed-deployment.md](closed-deployment.md) に記載する。今回の共通化でもこの手順は維持する。

## Container runtime requirements

sokoraを実行するcontainer環境は、最低限次を満たす。

- OCI imageを実行できる
- containerが `0.0.0.0:$PORT` でHTTPをlistenできる
- `PORT`、`DATABASE_URL`、`SOKORA_*`、`OIDC_*` 等をenvironment / secretとして注入できる
- 選択したDBへnetwork到達できる
- `GET /healthz` をreadiness checkとして利用できる
- 外部公開する場合はruntime側でHTTPS ingress / TLSを構成できる

image registry、container service、network、ingress/TLS、identity、secret store、managed DBそのものの作成、provider固有CLI/IaCはsokora repositoryの管理対象外とする。

application coreやDB access層へcloud provider固有SDK、metadata service、credential discovery、provider abstractionを追加しない。

## Database selection

| Backend | 想定topology | Persistent state | Replica |
| --- | --- | --- | --- |
| SQLite | standalone / single-instance container | `/app/data` をdurable filesystemへmount | 1 |
| PostgreSQL | external / managed PostgreSQL | DB service側 | 1..N |

### SQLite

SQLiteを利用する場合、database fileをcontainerのephemeral filesystemへ置かない。

1. writableで永続化されるfilesystemをcontainerの `/app/data` へmountする。
2. application replicaは1つだけ起動する。
3. `DATABASE_URL=sqlite:///data/sokora.db` を利用する。
4. startup migration完了後、`/healthz` が200を返すことを確認する。
5. backup/restoreは [SQLite database management](sqlite-database-management.md) の手順を利用する。

SQLite fileは通常のfilesystem上でfile locking等を利用する。object storage bucketをSQLite DB fileの直接配置先として扱わない。

container platformがSQLiteに必要なdurable filesystemを提供できない場合は、external PostgreSQLを利用する。

### External / managed PostgreSQL

externalまたはmanaged PostgreSQLも、sokoraからは標準PostgreSQLとして扱う。

概念上の手順はproviderに依存しない。

1. PostgreSQL databaseとapplication用credentialを用意する。
2. sokora containerからDB endpointへ到達できるnetworkを構成する。
3. DB側でTLSが必要な場合は接続URLのoptionを設定する。
4. credentialをsourceやimageへ埋め込まず、runtime secretとして `DATABASE_URL` を注入する。
5. sokora containerを起動する。
6. startupでAlembic migrationがheadまで完了することを確認する。
7. `/healthz` が200を返すことを確認する。
8. backup/restoreはPostgreSQL運用基盤側の標準手段を利用する。

例:

```text
DATABASE_URL=postgresql://user:password@db.example:5432/sokora
DATABASE_URL=postgresql://user:password@db.example:5432/sokora?sslmode=require
```

複数replicaで実行する場合は、全replicaが同じexternal PostgreSQLと同じruntime secret/configを利用する。consistency contractは [ADR 0003](adr/0003-multi-replica-runtime.md) を参照する。

## Startup and health

application startupはbackend共通でAlembic migrationを適用し、失敗時はstartupをabortする。fresh file-backed SQLiteだけinitial seedを作成し、PostgreSQLでは自動seedしない。

readiness endpointは認証不要の `GET /healthz`。DBへ到達でき、applicationが必要なschemaを確認できる場合だけ200を返す。詳細は [runtime.md](runtime.md) を参照する。

## Closed-network Docker deployment

閉域Dockerサーバー向けには、repository-free bundleとSQLite/PostgreSQL用Compose定義を実装済み。

```bash
VERSION=<version> make closed-bundle
```

imageの搬入、manifest/checksum検証、runtime env、persistent storage、upgrade/rollback、proxy、CI validationを含む正式手順は [Closed-network deployment](closed-deployment.md) を参照する。generic deploymentのためにこのclosed-network手順やartifactを削除・置換しない。
