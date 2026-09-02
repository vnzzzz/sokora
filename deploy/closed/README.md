# sokora closed-network deployment bundle

This directory is the runtime deployment unit for an isolated/closed network. It is generated from the same provider-neutral production image used by cloud deployments and does not require the development repository on the runtime host.

## Bundle contents

- `image.tar`: production image exported by `docker save`
- `image.tar.sha256`: transport-integrity checksum
- `manifest.env`: packaged image reference, image ID, and the explicitly supplied source revision of that image
- `load-image.sh`: manifest/checksum verification + `docker load` + image ID verification
- `compose.sqlite.yaml`: single-instance SQLite runtime
- `compose.postgresql.yaml`: external PostgreSQL runtime
- `compose.env.example`: non-secret deployment values
- `runtime.env.example`: application/runtime settings and secret placeholders

Docker Engine and Docker Compose v2 are the reference runtime. The application image itself has no cloud-provider dependency.

## 1. Load the image

```bash
./load-image.sh
```

`manifest.env` is mandatory. The loader rejects an incomplete/unsupported manifest before loading the archive, verifies `image.tar.sha256`, loads the image, and then verifies that the loaded immutable image ID matches the manifest.

Do not retag the image to `latest` for normal operations. Keep the immutable version tag shown by `manifest.env`; upgrade and rollback select that tag explicitly.

## 2. Install persistent configuration

Keep configuration and mutable data outside this bundle so replacing/removing a bundle cannot remove runtime state.

The reference procedure assumes the same non-root operator that runs `docker compose` owns the two deployment files. This lets Compose read the secret-bearing runtime env while keeping it private from other users.

```bash
operator_user="$(id -un)"
operator_group="$(id -gn)"
sudo install -d -m 0750 -o "$operator_user" -g "$operator_group" /etc/sokora
sudo install -m 0600 -o "$operator_user" -g "$operator_group" runtime.env.example /etc/sokora/runtime.env
sudo install -m 0640 -o "$operator_user" -g "$operator_group" compose.env.example /etc/sokora/deployment.env
```

Edit `/etc/sokora/runtime.env` and set the required authentication/OIDC/database/proxy values. `SOKORA_AUTH_SESSION_SECRET` must be a strong shared secret when authentication is enabled. If operations are intentionally performed as root or by a dedicated service account instead, give that operator equivalent read access and run all Compose commands consistently as that identity.

For SQLite, also create persistent host storage:

```bash
sudo install -d -m 0750 /var/lib/sokora
```

`/etc/sokora/deployment.env` contains `SOKORA_IMAGE`, host/container ports, the SQLite data directory, and the path to the runtime env file. Update it when those deployment values differ from the examples.

## 3A. Start SQLite

SQLite is supported only for one application instance. `compose.sqlite.yaml` fixes `DATABASE_URL` to `sqlite:///data/sokora.db` and mounts `SOKORA_DATA_DIR` at `/app/data`; the blank `DATABASE_URL` in `runtime.env.example` is intentionally overridden in this mode.

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.sqlite.yaml \
  -p sokora \
  up -d --pull never
```

## 3B. Start PostgreSQL

Set `DATABASE_URL` in `/etc/sokora/runtime.env` to the actual shared PostgreSQL URL before starting. The template intentionally leaves this value blank. `compose.postgresql.yaml` validates the container runtime value and exits before application startup unless it begins with a PostgreSQL scheme (`postgresql://`, `postgres://`, or an explicit `postgresql+...` SQLAlchemy driver URL). It never falls back to an unmounted SQLite database.

The application data directory is not mounted in this mode.

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.postgresql.yaml \
  -p sokora \
  up -d --pull never
```

PostgreSQL can be used by multiple application replicas when the surrounding deployment platform/load balancer is configured accordingly. The Compose adapter intentionally describes one process; replica orchestration belongs to the target environment.

## 4. Verify

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.sqlite.yaml \
  -p sokora \
  ps

curl -fsS http://127.0.0.1:8000/healthz
```

Use `compose.postgresql.yaml` in the command when PostgreSQL is selected. If `SERVICE_PORT` differs from `8000`, use that host port for the health request.

Application startup applies Alembic migrations automatically. Fresh file-backed SQLite also receives the standard initial seed; PostgreSQL does not auto-seed.

## SQLite backup before upgrade

Create a consistent backup with SQLite's backup API while the current container is running:

```bash
docker compose \
  --env-file /etc/sokora/deployment.env \
  -f compose.sqlite.yaml \
  -p sokora \
  exec -T sokora python - <<'PY'
import datetime
import pathlib
import sqlite3

source = pathlib.Path('/app/data/sokora.db')
backup_dir = pathlib.Path('/app/data/backups')
backup_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.datetime.now(datetime.UTC).strftime('%Y%m%dT%H%M%SZ')
target = backup_dir / f'sokora-pre-upgrade-{timestamp}.db'
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
print(target)
PY
```

Keep that backup until the new version has been accepted.

## Upgrade

1. Back up SQLite as above, or take the standard PostgreSQL database backup/snapshot outside sokora.
2. Copy in the new bundle and run its `./load-image.sh`.
3. Change `SOKORA_IMAGE` in `/etc/sokora/deployment.env` to the new immutable tag.
4. Run the same `docker compose ... up -d --pull never` command using the new bundle's Compose file.
5. Verify `/healthz` and the required user flows.
6. Keep the previous image/bundle and database backup until acceptance is complete.

Because startup owns `alembic upgrade head`, an image upgrade may also upgrade the database schema.

## Rollback

Changing only the image tag is safe only when the old application is compatible with the already-upgraded database schema. Do not assume that compatibility.

For SQLite after a schema-changing upgrade:

1. Stop sokora with `docker compose ... down`.
2. Restore the pre-upgrade backup to the persistent `sokora.db` path while the application is stopped; remove stale `sokora.db-wal` / `sokora.db-shm` files if present.
3. Set `SOKORA_IMAGE` back to the previous immutable tag.
4. Start the previous image and verify `/healthz` and application behavior.

For PostgreSQL, use the environment's database backup/restore or snapshot mechanism when schema rollback is required. sokora does not automatically run Alembic downgrade during image rollback.

## Proxy

The bundle and Compose files do not contain a proxy implementation. If the runtime requires a forward proxy, set standard `HTTP_PROXY`, `HTTPS_PROXY`, lowercase variants, and `NO_PROXY`/`no_proxy` in `/etc/sokora/runtime.env`. Internal database and OIDC endpoints that must bypass the proxy belong in `NO_PROXY`.
