# Getting started

## Reference environment

開発のreference environmentはVS Code Dev Containerです。Python / uv / Node.js / agent toolingをcontainer側へ閉じ込め、host環境との差を減らします。

Make targetは実行責務ごとに2つのcontextへ分離しています。

- `workspace`: checked-out sourceへ直接作用するdevelopment command。Dev Containerでは自動的にこのcontextを選択します。
- `host`: Docker image / container / deployment packageを扱うcommand。repository rootで通常の`make`を実行した場合はこちらが既定です。

CIも同じinterfaceを利用し、test/quality/migrationは`workspace`、image/deployment検証は`host`を明示的に選択します。

直接hostでdevelopment commandを実行することもできますが、その場合はPython 3.13、uv、Node.js/npmとrepository scriptsが利用するUnix commandを用意し、`SOKORA_MAKE_CONTEXT=workspace`を明示する必要があります。repository CIとDev Containerが検証対象であり、任意のhost環境を同一条件として保証するものではありません。

## Setup

Dev Containerを開いた後、repository rootで:

```bash
cp .env.sample .env
```

Dev Containerでは`SOKORA_MAKE_CONTEXT=workspace`が設定済みなので、development targetは従来どおり実行できます。`VERSION`は不要です。

依存関係とfrontend assetを準備して起動します。

```bash
make install
make run
```

browserで http://localhost:8000 を開きます。

既定DBは`sqlite:///data/sokora.db`です。startupでAlembic migrationを適用し、fresh file-backed SQLiteだけinitial seedを作成します。

## Make contexts

### Workspace — Dev Container

Dev Container内の`make help`にはworkspace targetだけが表示されます。

| Command | 用途 |
| --- | --- |
| `make run` | development serverをreload付きで起動 |
| `make test` | unit / API / page / E2E test |
| `make quality` | Ruff lint + format check + mypy |
| `make format` | import整理とRuff formatを適用 |
| `make seed` | attendance sample dataを投入 |
| `make assets` | Tailwind / vendor JS assetをbuild |
| `make holiday-cache` | 祝日cacheを生成 |
| `make migrate` | Alembicをheadへ更新 |

Dev Container外で同じtargetを意図的に使う場合はcontextを明示します。

```bash
make SOKORA_MAKE_CONTEXT=workspace quality
```

### Docker host — macOS / WSL / Linux

hostのrepository rootでは`host` contextが既定で、`make help`にはDocker host targetだけが表示されます。

| Command | 用途 |
| --- | --- |
| `make build` | unversioned production imageをbuild |
| `make dev-build` | Dev Container Dockerfileをrepository root contextでbuild |
| `make dev-shell` | 起動中のDev Containerへattach |
| `make docker-build` | version付きproduction imageをbuild |
| `make docker-run` | production imageをlocal Dockerで起動 |
| `make docker-stop` | local production containerを停止 |
| `make closed-bundle` | 閉域向けbundleをbuild/package |
| `make package-closed-bundle` | build済みimageから閉域向けbundleをpackage |

versioned production image/packageを扱うtargetでは`VERSION`が必須です。

```dotenv
VERSION=dev
```

root `Makefile`はcontext dispatcherで、共通設定は`make/common.mk`、各targetは`make/workspace.mk`と`make/host.mk`にあります。

## Database

local開発ではSQLiteが既定です。PostgreSQLを使う場合は`.env`の`DATABASE_URL`を変更します。

```dotenv
DATABASE_URL=postgresql://sokora:password@db.example:5432/sokora
```

backendごとの制約は [Database](database.md)、deployment時の選択は [Deployment](deployment.md) を参照してください。

## Authentication

authentication guardの既定値はdisabledです。OIDC / local adminを有効化する場合は [Authentication](authentication.md) と `.env.sample` を参照してください。

## Before a pull request

Dev Container内で、変更箇所に応じたtestを実行したうえで少なくとも次を通します。

```bash
make format
make quality
make test
```

repository固有のagent / review ruleは [AGENTS.md](../AGENTS.md) を参照してください。
