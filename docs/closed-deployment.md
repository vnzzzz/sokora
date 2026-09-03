# Closed-network deployment

## Scope

閉域環境でも、GCP/AWS/Azureと同じprovider非依存production OCI imageを利用する。application codeやDockerfileを閉域向けに分岐せず、差分はimageの配送方法、runtime env/secret、network、persistent dataへ閉じ込める。

runtime自体の共通contractは [runtime.md](runtime.md) を参照する。本書では閉域向けdeployment adapterと運用境界を定義する。

## Deployment unit

runtime hostへ持ち込む標準単位は `scripts/deployment/package_closed_bundle.sh` が生成するbundleとする。

bundleには以下だけを含める。

- production imageの `docker save` archive
- archiveのSHA-256 checksum
- image reference / image ID / **そのimageをbuildしたsource revision** を記録したmanifest
- mandatory manifestとchecksumを検証後に `docker load` し、manifestのimage IDと一致することまで確認するloader
- SQLite / PostgreSQL用の薄いDocker Compose定義
- deployment/runtime env template
- runtime host向けoperator guide

開発repo、tests、docs全体、devcontainer、agent設定、Node/uv等のbuild toolingはruntime deployment unitへ含めない。production image自体のartifact boundaryもこの方針と一致する。

`SOURCE_REVISION` はpackagingを行ったcheckoutから暗黙推測しない。prebuilt imageをbundle化するときは、そのimageをbuildした40文字Git commitをcallerが明示する。これにより「古い/外部build image + 現在のpackaging checkout」の組合せでも誤ったprovenanceをmanifestへ記録しない。

bundle再生成は既存directoryを先に削除しない。同一filesystem上のsibling temporary directoryへ全artifactを生成し、manifestを最後に書いた後だけ完成済みbundleへ切り替える。途中で `docker save`、checksum、copy等が失敗した場合はprevious known-good bundleを保持し、partial bundleを正式な出力先へ残さない。

## Build location

### 外部でbuildして搬入する場合

推奨経路。source checkoutからversion付きimageをbuildしてそのままbundle化する場合は、`closed-bundle` がbuild対象checkoutのrevisionを自動でmanifestへ渡す。

```bash
VERSION=2026.09.02 make closed-bundle
```

すでに別工程でbuild済みのimageをbundle化する場合は、そのimageのsource revisionを明示する。

```bash
VERSION=2026.09.02 \
SOURCE_REVISION=<40-character-build-commit> \
make package-closed-bundle
```

生成先は既定で `dist/sokora-2026.09.02-closed/`。このdirectoryだけを承認済み媒体等でruntime側へ搬入する。

### 閉域内でbuildする場合

閉域内に依存取得可能なbuild hostを用意し、source checkout/release sourceから同じroot `Dockerfile` をbuildする。

```bash
VERSION=2026.09.02 make closed-bundle
```

sourceはbuild hostだけで利用し、runtime hostへは生成済みbundleだけを渡す。閉域専用Dockerfileは作らない。

## Registry delivery

閉域内registryへ到達できる場合は `docker save/load` の代わりにimmutable version tagをregistry経由で配送してよい。重要なのは配送経路ではなく、同一production imageをそのまま実行すること。

`latest` のようなmutable tagだけでupgrade/rollbackを運用しない。release/versionまたはcommitに対応するimmutable tagを保持する。

## Runtime state boundary

image/bundle lifecycleとmutable stateを分離する。

| State | Location/contract |
| --- | --- |
| deployment values | `/etc/sokora/deployment.env` 等。image tag、publish port、data/env path |
| application secret/config | `/etc/sokora/runtime.env` 等。bundle外で権限制御し、Compose operatorがread可能なownership/modeにする |
| SQLite DB | `/var/lib/sokora` 等のpersistent host storageを `/app/data` へmount |
| PostgreSQL data | external PostgreSQL。application container filesystemへ保持しない |
| image | immutable version tag。old versionをrollback期間中保持 |

bundle内のexample env fileをそのままsecret storeとして扱わない。referenceのnon-root Docker operator運用では `/etc/sokora/runtime.env` をoperator owner・`0600`、deployment envをoperator owner・`0640` とし、Composeが`env_file`を読めることを保証する。rootや専用service accountで運用する場合は、そのidentityへ同等のread権限を与え、Compose実行identityも統一する。

## SQLite

SQLiteはsingle-instance runtimeだけをsupportする。`deploy/closed/compose.sqlite.yaml` はpersistent host directoryを `/app/data` へbind mountし、`DATABASE_URL=sqlite:///data/sokora.db` を固定する。generic `runtime.env.example` の `DATABASE_URL` は意図的にblankであり、SQLite adapterが明示的にoverrideする。

upgrade前は稼働中DBの単純なfile copyではなくSQLite backup APIを利用する。bundle付属READMEに、production image内のPython標準`sqlite3`からconsistent backupを作成する手順を記載する。

startupでAlembic migrationが適用されるため、schema-changing upgrade後のrollbackでは原則としてpre-upgrade DB backupも同時にrestoreする。old imageへ戻すだけでschema互換性が保たれるとは仮定しない。

## PostgreSQL

`deploy/closed/compose.postgresql.yaml` はapplication側のpersistent data volumeを持たず、`runtime.env` の `DATABASE_URL` でexternal PostgreSQLへ接続する。template値はblankのままとし、operatorが実URLを設定する。

PostgreSQL adapterはapplication startup前に `DATABASE_URL` を検証し、未設定またはPostgreSQL scheme以外ならexitする。これにより設定漏れ時にdefault SQLiteへfallbackしてunmounted container filesystemへDBを作ることを禁止する。

DB backup/restoreはPostgreSQL運用基盤側の標準手段を利用する。application imageに`pg_dump`やvendor固有backup clientを追加しない。

shared PostgreSQLを使うmulti-replica contractは [ADR 0003](adr/0003-multi-replica-runtime.md) に従う。Compose adapterは閉域runtimeの最小1-process定義であり、replica orchestration/load balancerは対象環境側の責務とする。

## Upgrade contract

1. current versionのDB backup/snapshotを取得する。
2. new immutable imageをbundleまたはregistryからload/pullする。
3. deployment envの `SOKORA_IMAGE` をnew tagへ変更する。
4. new bundleの同じCompose adapterでcontainerをreplaceする。
5. startup migration完了後、`/healthz` と主要操作を確認する。
6. acceptanceまではold imageとDB backupを保持する。

application startupがmigrationを所有するため、operatorが別系統のmanual schema bootstrapを実行しない。

## Rollback contract

- DB schema互換性が確認できる場合のみimage tagをold versionへ戻すだけのrollbackを許容する。
- schema-changing upgrade後は、applicationを停止してpre-upgrade DB stateもrestoreしてからold imageを起動する。
- automatic Alembic downgradeをimage rollbackの暗黙動作にはしない。

この方針によりimage rollbackとDB rollbackの境界を明示し、old application + new incompatible schemaの組合せを避ける。

## Proxy

閉域proxyはimageへ焼き込まない。build時は既存Makefileの `proxy` / `NO_PROXY` contract、runtime時は標準 `HTTP_PROXY` / `HTTPS_PROXY` / lowercase variants / `NO_PROXY` をenvironment injectionする。

internal PostgreSQL/OIDC endpoint等、proxyを経由させない宛先はdeployment環境側で `NO_PROXY` に追加する。proxy有無で別Dockerfile・別application codeを持たない。

## Validation

`Closed deployment` CIでは以下を保証する。

- 同じproduction imageからrepository-free bundleを生成できる
- callerが明示したbuild revisionがmanifestへそのまま記録される
- packaging途中失敗時にprevious known-good bundleを失わない
- manifest欠落を`docker load`前に拒否する
- image archive checksumを検証して`docker load`でき、loaded image IDがmanifestと一致する
- bundle内にrepo/test/dev toolingを含めない
- PostgreSQL adapterはblank/non-PostgreSQL `DATABASE_URL` をfail-closedで拒否する
- bundleのSQLite Compose adapterだけでimageを再起動し `/healthz` が成功する
- PostgreSQL自体のproduction image接続contractは既存PostgreSQL jobで継続検証する

bundle sourceは `deploy/closed/`、packaging entrypointは `scripts/deployment/package_closed_bundle.sh` とする。
