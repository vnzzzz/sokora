# Getting started

## Reference environment

開発のreference environmentはVS Code Dev Containerです。Python / uv / Node.js / agent toolingをcontainer側へ閉じ込め、host環境との差を減らします。

Make targetは実行責務で分離しています。

- `workspace`: checked-out sourceへ直接作用するdevelopment command。Dev Containerでは自動選択
- `host`: Docker image / container / deployment packageを扱うcommand。repository rootでは既定

直接hostでdevelopment commandを実行することもできますが、その場合はPython 3.13、uv、Node.js/npmとrepository scriptsが利用するUnix commandを用意し、`SOKORA_MAKE_CONTEXT=workspace`を明示します。repository CIとDev Containerが検証対象であり、任意のhost環境を同一条件として保証するものではありません。

## Setup

Dev Containerを開いた後、repository rootで:

```bash
cp .env.sample .env
make install
make run
```

browserで http://localhost:8000 を開きます。

既定DBは`sqlite:///data/sokora.db`です。startupでAlembic migrationを適用し、fresh file-backed SQLiteだけinitial seedを作成します。

## Make contexts

利用可能なtargetは、その環境で`make help`を実行して確認します。Dev Containerではworkspace target、hostではDocker host targetだけが表示されます。

Dev Container外からworkspace targetを意図的に実行する場合:

```bash
make SOKORA_MAKE_CONTEXT=workspace quality
```

version付きproduction imageやclosed-network bundleを扱うhost targetでは`VERSION`が必要です。

```bash
VERSION=dev make docker-build
```

root `Makefile`はcontext dispatcherで、共通設定は`make/common.mk`、各targetは`make/workspace.mk`と`make/host.mk`にあります。

## Database and authentication

local開発ではSQLiteが既定です。PostgreSQLを使う場合は`.env`の`DATABASE_URL`を変更します。backendごとの制約は [Database](database.md)、deployment時の選択は [Deployment](deployment.md) を参照してください。

authentication guardの既定値はdisabledです。OIDC / local adminを有効化する場合は [Authentication](authentication.md) と `.env.sample` を参照してください。

## Before a pull request

Dev Container内で、変更箇所に応じたtestを実行したうえで少なくとも次を通します。

```bash
make format
make quality
make test
```

repository固有のagent / review ruleは [AGENTS.md](../AGENTS.md) を参照してください。
