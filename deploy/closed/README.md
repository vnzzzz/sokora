# sokora closed-network deployment bundle

このbundleは、閉域Docker hostでsokoraを実行するためのruntime deployment unitです。source repositoryは不要です。

## Contents

| File | Purpose |
| --- | --- |
| `image.tar` | production OCI image |
| `image.tar.sha256` | checksum |
| `manifest.env` | image reference / image ID / source revision |
| `load-image.sh` | verify + `docker load` |
| `compose.sqlite.yaml` | SQLite runtime |
| `compose.postgresql.yaml` | external PostgreSQL runtime |
| `compose.env.example` | deployment values |
| `runtime.env.example` | application settings / secrets |

reference runtimeはDocker Engine + Docker Compose v2です。

## 1. Verify and load image

```bash
./load-image.sh
```

loaderはmanifest、SHA-256 checksum、load後のimage IDを検証します。通常運用で`latest`へretagせず、`manifest.env`のimmutable version tagを使ってください。

## 2. Install persistent configuration

bundleとruntime stateを分離します。

```bash
operator_user="$(id -un)"
operator_group="$(id -gn)"

sudo install -d -m 0750 -o "$operator_user" -g "$operator_group" /etc/sokora
sudo install -m 0600 -o "$operator_user" -g "$operator_group" \
  runtime.env.example /etc/sokora/runtime.env
sudo install -m 0640 -o "$operator_user" -g "$operator_group" \
  compose.env.example /etc/sokora/deployment.env
```

rootや専用service accountで運用する場合も、Compose実行identityへ同等のread権限を与えます。

`/etc/sokora/runtime.env`へauthentication / OIDC / DB / proxy設定、`/etc/sokora/deployment.env`へimage tag / port / pathを設定します。

authentication guard(`SOKORA_AUTH_ENABLED=true`)を有効にする場合、またはguardが無効でも`SOKORA_LOCAL_AUTH_ENABLED=true`かつlocal admin username/passwordを設定してlocal admin loginを使う場合は、`SOKORA_AUTH_SESSION_SECRET`へstrong secretを設定します。空欄のままlocal admin credentialだけ設定するとstartupで拒否されます。

DB-backed OIDC設定を利用する場合は`SOKORA_AUTH_CONFIG_ENCRYPTION_KEY`も設定します。

```bash
set -a
. ./manifest.env
set +a

docker run --rm "$IMAGE_REF" \
  python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

この鍵はDB backupと分離して保管し、複数replicaでは同じ値を使用します。既存deploymentで`auth_config` rowがまだない場合はlegacy `OIDC_*` environmentが引き続き有効です。admin画面からsave / disable / unlinkした後はDBがOIDC sourceになります。

## 3A. Start with SQLite

SQLiteはsingle-instanceです。

```bash
sudo install -d -m 0750 /var/lib/sokora

docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.sqlite.yaml \
  -p sokora \
  up -d --pull never
```

Composeはhostのpersistent data directoryを`/app/data`へmountし、`DATABASE_URL=sqlite:///data/sokora.db`を設定します。

## 3B. Start with PostgreSQL

先に`/etc/sokora/runtime.env`へactual PostgreSQL URLを設定します。

```dotenv
DATABASE_URL=postgresql://user:password@db.example:5432/sokora
```

起動:

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.postgresql.yaml \
  -p sokora \
  up -d --pull never
```

PostgreSQL Composeはexplicit PostgreSQL URL以外を拒否し、default SQLiteへfallbackしません。application data volumeはmountしません。

## 4. Verify

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.sqlite.yaml \
  -p sokora \
  ps

curl -fsS http://127.0.0.1:8000/healthz
```

PostgreSQLの場合は`compose.postgresql.yaml`を指定します。`SERVICE_PORT`を変更した場合はhealth requestのportも合わせます。

startupでAlembic migrationを自動適用します。fresh file-backed SQLiteだけinitial seedを作成し、PostgreSQLはauto-seedしません。

## SQLite backup before upgrade

稼働中DBの単純copyではなくSQLite backup APIを使います。

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.sqlite.yaml \
  -p sokora \
  exec -T sokora python - <<'PY'
import datetime
import pathlib
import sqlite3

source = pathlib.Path("/app/data/sokora.db")
backup_dir = pathlib.Path("/app/data/backups")
backup_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
target = backup_dir / f"sokora-pre-upgrade-{timestamp}.db"

with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)

print(target)
PY
```

new versionのacceptanceまでbackupを保持します。

## Upgrade

1. SQLite backupまたはPostgreSQL backup / snapshotを取得
2. new bundleを搬入し`./load-image.sh`
3. `/etc/sokora/deployment.env`の`SOKORA_IMAGE`をnew immutable tagへ変更
4. new bundleの同じCompose fileで`up -d --pull never`
5. `/healthz`と必要なuser flowを確認
6. previous image / bundle / DB backupをacceptanceまで保持

startupが`alembic upgrade head`を実行するため、image upgradeでschemaも進む場合があります。

## Rollback

image tagだけを戻せるのは、previous applicationとcurrent DB schemaの互換性が確認できる場合だけです。

schema-changing upgrade後:

1. applicationを停止
2. pre-upgrade DB stateをrestore
3. `SOKORA_IMAGE`をprevious immutable tagへ戻す
4. previous imageを起動
5. `/healthz`とapplication behaviorを確認

SQLiteをfile restoreする場合はapplication停止中にpersistent `sokora.db`を置換し、古い`-wal` / `-shm`が残っていれば除去します。

PostgreSQLはDB platformのbackup / snapshotからrestoreします。image rollback時にAlembic downgradeを自動実行しません。

## Proxy

forward proxyが必要な場合は`/etc/sokora/runtime.env`へ標準`HTTP_PROXY` / `HTTPS_PROXY` / lowercase variants / `NO_PROXY`を設定します。

internal DB / OIDC endpoint等、proxyを経由させない宛先は`NO_PROXY`へ追加してください。
