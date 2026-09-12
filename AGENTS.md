# sokora repository guide

このファイルはcoding agent向けの**repository固有情報**だけを扱います。一般的なIssue workflow、planning、testing、technical writing、reportingはDev Containerの`vnzzzz/agent-skills`を利用し、user instructionとrepository固有ruleを優先してください。

## Project

sokoraは勤怠種別・勤務場所をカレンダーUIで扱うFastAPI applicationです。

- Python 3.13 / uv
- FastAPI / Jinja2 / HTMX / Alpine.js
- SQLAlchemy / Alembic
- SQLite / PostgreSQL
- Tailwind CSS / daisyUI
- Ruff / mypy / pytest / Playwright

## Source of truth

taskに関係する一次情報を実装前に確認します。

- documentation入口: `docs/README.md`
- local setup: `docs/getting-started.md`
- architecture / state boundary: `docs/architecture.md`
- authentication: `docs/authentication.md`
- JSON API: `docs/api.md`
- DB / migration / transaction: `docs/database.md`
- SSR / HTMX / templates: `docs/ui.md`
- production runtime: `docs/runtime.md`
- generic deployment: `docs/deployment.md`
- closed-network運用: `docs/closed-deployment.md`
- SQLite backup / restore: `docs/sqlite-database-management.md`
- architecture decisions: `docs/adr/`
- dependencies / tool config: `pyproject.toml`, `uv.lock`
- commands: `Makefile`, `scripts/`

docsと実装が食い違う場合は推測で合わせず、live implementationを確認して同じ変更で正本を更新します。

## Code responsibilities

- `app/routers/pages/`: HTML / HTMX adapters
- `app/routers/api/v1/`: JSON API adapters
- `app/services/`: business rule / transaction coordination / read model
- `app/crud/`: data access
- `app/models/`, `app/db/`: persistence model / runtime
- `app/templates/`: Jinja templates
- `app/static/`: application static source
- `scripts/migration/`: Alembic
- `scripts/seeding/`: seed
- `builder/`: frontend asset build source
- `deploy/closed/`: closed-network distribution assets

既存責務を確認せず新しいlayer / abstractionを追加しません。

## Repository-specific constraints

- generated Tailwind/vendor assetを直接編集せず、sourceと既存build flowを変更する
- DB model変更では既存Alembic revisionを書き換えず、新しいmigrationを追加する
- `.env`、credential、token等のsecretをcommitしない
- `DATABASE_URL`の既定は`sqlite:///data/sokora.db`
- SQLiteはsingle-instance。horizontal multi-replicaはshared PostgreSQL
- page/HTMXとJSON APIのtransport責務を混ぜない
- write transaction / business ruleはservice境界を優先する
- provider固有SDK / deployment abstractionをapplication coreへ持ち込まない
- closed-network asset変更時はoperator guideと`docs/closed-deployment.md`を同期する
- architecture decisionを変更するときは既存ADRを確認し、必要なら新しいADRでsupersedeする
- comment/docstringは処理の言い換えではなく、codeだけでは失われる理由・制約・不変条件・resource lifetimeを残す

## Common commands

Dev Container workspaceは`/app`です。

```bash
make run
make test
make quality
make format
make seed
make assets
```

必要な個別checkは`make lint`、`make format-check`、`make typecheck`。PR前はrepository標準CIで成立する状態にします。

Python source/testを変更したcommitまたはpushの前は、**必ず先に `make format` を実行し、その後 `make quality` を実行します**。`make quality` のformat stepはcheck-onlyで自動修正しないため、formatを省略したままCIへ送らないこと。

## GitHub workflow

- baseは`main`
- short-lived branchを最新`main`から作成
- 原則1 Issue = 1 PR。強く結合した変更だけreviewabilityを損なわない範囲でまとめる
- PR本文に`Closes #<issue>`
- unrelated cleanupを混ぜない
- mainへの統合はsquash mergeを基本とする
- userから明示的な依頼がない限りmergeしない
- CIとreview feedbackを確認し、actionable findingを修正・再検証する

Codexはこの`AGENTS.md`、Claude Codeはroot `CLAUDE.md`からこのファイルを参照します。
