# sokora repository guide

このファイルは、sokoraで作業するcoding agent向けの**リポジトリ固有情報**だけを扱う。
一般的なIssue駆動、変更計画、実装原則、テスト設計、command実行、debugging、報告方法は、Dev Containerの`agent-dev` Featureが導入する`vnzzzz/agent-skills`を利用する。リポジトリ固有ルールとtask/user instructionを優先し、一般ルールをこのファイルへ重複記載しない。

## Project

sokoraは勤怠種別・勤務場所をカレンダーUIで扱うWebアプリケーション。

- Python 3.13
- FastAPI / Jinja2
- HTMX / Alpine.js
- SQLAlchemy / Alembic
- SQLite（既定runtime。接続先は`DATABASE_URL`で設定）
- PostgreSQL
- uv
- pytest / pytest-playwright / Ruff / mypy
- Tailwind CSS

## Source of truth

変更前にtaskに関係する一次情報を読む。文書の責務分担は最初に`docs/README.md`を確認する。主要文書はADRと画像を除いて`docs/`直下へ集約する。

- docs入口 / SSoT map: `docs/README.md`
- 全体要件: `docs/requirements.md`
- DB要件: `docs/database.md`
- API要件: `docs/api.md`
- UI要件: `docs/ui.md`
- template構成: `docs/templates.md`
- deployment入口 / support status: `docs/deployment.md`
- production runtime contract: `docs/runtime.md`
- closed-network運用: `docs/closed-deployment.md`
- SQLite backup/restore運用: `docs/sqlite-database-management.md`
- architecture decision: `docs/adr/`
- 依存関係・tool設定: `pyproject.toml`, `uv.lock`
- 開発command: `Makefile`, `scripts/`

Issueや実装とdocsが食い違う場合は、推測で合わせず、taskの完了条件へ影響する差異を確認して必要なSSoTを同じ変更で更新する。未実装の機能やdeployment adapterを実装済みとして扱わない。

## Architecture map

主な責務は次のとおり。

```text
app/main.py
  ├─ app/routers/pages/   -> HTML / HTMX adapter
  └─ app/routers/api/v1/ -> JSON API adapter
          │
          ├─ write use cases -> app/services/ -> app/crud/
          └─ read paths      -> read service / app/crud/ / view helper
                                      └─ app/models/ + app/db/

app/templates/
  ├─ layout/
  ├─ pages/
  └─ components/
```

- `app/schemas/`: API等のPydantic schema
- `app/core/`: application設定
- `app/utils/`: 特定domainへ閉じない共通処理
- `app/tests/`: unit / API / page / E2E tests
- `scripts/migration/`: Alembic
- `scripts/seeding/`: seed data
- `builder/`: Tailwind build source
- `deploy/closed/`: closed-network deployment adapter assets

writeのtransaction/business ruleはservice境界を優先する。readは画面/集計の複雑さに応じてdedicated read serviceまたは既存CRUD/helperを利用する。既存の責務分離を確認せず新しいlayerやpatternを追加しない。

## Repository-specific constraints

- Tailwind等の生成物を直接編集しない。sourceを変更して既存build flowを使う。
- DB modelを変更する場合、既存Alembic versionを書き換えず、新しいmigrationを追加する。
- `.env`、credential、token等のsecretをcommitしない。`.env.sample`にはsample値だけを置く。
- `DATABASE_URL`の既定値は`sqlite:///data/sokora.db`。`data/sokora.db`はruntime dataとして扱い、sourceとしてcommitしない。
- SQLiteはsingle-instance runtime用。horizontal multi-replicaはshared PostgreSQLを利用する。
- UI変更では既存のJinja/HTMX/Alpine patternと`docs/ui.md`を確認する。
- API変更では`docs/api.md`とpage側への影響を確認する。
- DB変更では`docs/database.md`、model、migration、seed、testの整合を確認する。
- production/deployment変更では`docs/deployment.md`と`docs/runtime.md`を確認し、provider固有処理をapplication coreへ持ち込まない。
- 横断的なarchitecture判断は既存`docs/adr/`を確認し、必要ならADRを追加する。
- comment/docstringは処理の言い換えではなく、codeだけでは失われる判断理由、制約、不変条件、resource lifetimeを残す。公開関数・型ではcallerが守る条件やfailure boundaryが重要なら明示する。

## Common commands

Dev Containerのworkspaceは`/app`。

```bash
uv sync --locked
make run
make test
make seed
make assets
make quality
make format
```

Pythonの品質ゲートはRuff（lint / import sorting / format）とmypy（typecheck）に統一する。個別確認が必要な場合は`make lint` / `make format-check` / `make typecheck`を使う。

変更範囲に直接関係するtest/checkを先に実行し、PR前にはrepositoryの標準CIで成立する状態にする。

## GitHub workflow

- base branchは`main`。
- 原則 **1 Issue = 1 PR**。ただし変更が強く結合し、分割すると実装・検証が重複するIssueは、レビュー性・ロールバック性を損なわない範囲で1 PRにまとめてよい。
- short-lived branchを`main`から作成する。
- PR本文に対応する`Closes #<issue>`をすべて記載する。
- unrelated cleanupを同じPRへ混ぜない。
- mainへの統合は**squash mergeを基本**とし、履歴上の理由がある場合だけrebaseを検討する。
- userから明示的な依頼がない限り、agentはmergeしない。
- CIとreview feedbackを確認し、actionableな指摘は修正・再検証する。

## Agent instructions

- Codexはこの`AGENTS.md`をrepo-local instructionとして利用する。
- Claude Codeはrootの`CLAUDE.md`からこのファイルをimportする。
- tool固有のpromptへsokoraの一般workflowを複製しない。
- `agent-skills`で扱える一般的な手順はそちらへ委譲し、このファイルにはsokora固有の事実・制約・入口だけを残す。
