# Getting started

## Reference environment

開発のreference environmentはVS Code Dev Containerです。Python / uv / Node.js / agent toolingをcontainer側へ閉じ込め、host環境との差を減らします。

直接hostで実行する場合は少なくともPython 3.13、uv、Node.js/npmとrepository scriptsが利用するUnix commandが必要です。repository CIとDev Containerが検証対象であり、任意のhost環境を同一条件として保証するものではありません。

## Setup

Dev Containerを開いた後、repository rootで:

```bash
cp .env.sample .env
```

sampleはlocal開発用の `SERVICE_PORT=8000` を含み、`make run` / `make test` / `make quality` 等のdevelopment targetでは `VERSION` は不要です。

`VERSION` はversioned production image/packageを扱うtargetでだけ必須です。

```dotenv
VERSION=dev
```

依存関係とfrontend assetを準備して起動します。

```bash
make install
make run
```

browserで http://localhost:8000 を開きます。

既定DBは`sqlite:///data/sokora.db`です。startupでAlembic migrationを適用し、fresh file-backed SQLiteだけinitial seedを作成します。

## Common commands

| Command | 用途 |
| --- | --- |
| `make run` | development serverをreload付きで起動 |
| `make test` | unit / API / page / E2E test |
| `make quality` | Ruff lint + format check + mypy |
| `make format` | import整理とRuff formatを適用 |
| `make seed` | attendance sample dataを投入 |
| `make assets` | Tailwind / vendor JS assetをbuild |
| `make migrate` | Alembicをheadへ更新 |
| `make docker-build` | version付きproduction imageをbuild |
| `make docker-run` | production imageをlocal Dockerで起動 |
| `make closed-bundle` | 閉域向けbundleを生成 |

全targetと変数は`make help`または`Makefile`を参照してください。

## Database

local開発ではSQLiteが既定です。PostgreSQLを使う場合は`.env`の`DATABASE_URL`を変更します。

```dotenv
DATABASE_URL=postgresql://sokora:password@db.example:5432/sokora
```

backendごとの制約は [Database](database.md)、deployment時の選択は [Deployment](deployment.md) を参照してください。

## Authentication

authentication guardの既定値はdisabledです。OIDC / local adminを有効化する場合は [Authentication](authentication.md) と `.env.sample` を参照してください。

## Before a pull request

変更箇所に応じたtestを実行したうえで、少なくとも次を通します。

```bash
make quality
make test
```

repository固有のagent / review ruleは [AGENTS.md](../AGENTS.md) を参照してください。
