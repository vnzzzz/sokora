# 開発ルール

本ドキュメントは sokora の日々の開発運用ルールです。`AGENTS.md` を入口に、`rules/coding.md` / `rules/testing.md`、必要に応じて `docs/adr/*.md` を併せて参照してください。

## 基本方針
- **TDD 徹底**: 受け入れレベルのテスト（API/ページ/E2E）→サービス/ユーティリティの順にまず失敗させ、最小実装でグリーンにする。
- **ドキュメント優先**: 要件や仕様の変更がある場合は `docs/requirements.md`、`docs/db/requirements.md`、`docs/ui/requirements.md`、`docs/api/requirements.md` を先に更新する。
- **責務分離の維持**: `models` / `schemas` / `crud` / `services` / `routers` / `templates` / `utils` の役割を混ぜない。
- **生成物・環境を壊さない**: Alembic 既存バージョンは書き換えず、Tailwind 生成 CSS などビルド成果物は直接編集しない。

## 進め方（1 ストーリー）
1. `AGENTS.md` の指示と SSoT（`docs/requirements.md` / `docs/db/requirements.md` / `docs/ui/requirements.md` / `docs/api/requirements.md`）を確認し、必要ならドキュメントを更新する案をまとめる。
2. 影響するレイヤーに応じて失敗するテストを追加・更新する（例: `app/tests/routers/api/v1/`, `app/tests/routers/pages/`, `app/tests/services/`, `app/tests/utils/`, `app/tests/e2e/`）。
3. `services` → `crud` → `schemas` / `templates` の順で最小実装を入れる。DB モデル変更時は Alembic で新規マイグレーションを追加する。
4. UI 変更時は `app/templates/` の構造（layout → pages → components/partials）を守り、HTMX/Alpine のパターンに倣う。
5. `./scripts/testing/run_test.sh` を基本としてテストを実行する。E2E にはサーバ起動が必要な場合があるため、必要に応じて `make run` を併用する。

## ブランチ / PR チェックリスト
- [ ] `README.md` / `docs/*` / `rules/*` / `AGENTS.md` など一次情報源を更新した。
- [ ] DB 変更があれば Alembic マイグレーションを追加し、破壊的変更や既存バージョンの書き換えをしていない。
- [ ] `black` / `isort` / `ruff` / `mypy` にかかるフォーマット・静的解析上の警告を解消した。
- [ ] `./scripts/testing/run_test.sh`（または影響範囲の pytest）を実行し、失敗理由が残っていない。
- [ ] `TODO(name): [ ] ...` の形式で未対応事項を明示した。

## よく使うコマンド
| 目的 | コマンド | 備考 |
| --- | --- | --- |
| 依存インストール | `make install` | Poetry + Tailwind builder のセットアップ。 |
| 開発サーバ起動 | `make run` | Uvicorn リロード付き。初回は Tailwind/DB の準備を実施。 |
| DB シード | `make seed` | `scripts/seeding/run_seeder.sh` 経由。 |
| テスト一括 | `./scripts/testing/run_test.sh` | 事前/事後クリーンアップ込み。 |
| Tailwind ビルド | `make assets` | 生成 CSS は直接編集しない。 |

## DB / データ管理
- SQLite を `data/sokora.db` に配置。存在しない場合は起動・ビルド時に自動生成＋シードされる。
- 既存 Alembic マイグレーションの編集は禁止。スキーマ変更時は新しいバージョンを追加する。
- `.env` に本番向け値を埋め込まない。必要なら `.env.sample` にサンプル値を追記する。

## ディレクトリ責務
| ディレクトリ | 役割 / 注意点 |
| --- | --- |
| `app/main.py` | FastAPI エントリポイント。ルーター/テンプレート/静的ファイル設定を集約。 |
| `app/core/` | 設定値の読み込み。環境変数名の互換性に注意。 |
| `app/db/` | SQLAlchemy セッションと Alembic と整合したモデル。 |
| `app/models/` | DB モデル。 |
| `app/schemas/` | API 入出力の Pydantic スキーマ。 |
| `app/crud/` | DB アクセス。ビジネスロジックは `services` へ。 |
| `app/services/` | ユースケース実装。ルーターから呼ばれる。 |
| `app/routers/api/v1/` | JSON API のルーター。 |
| `app/routers/pages/` | HTML ページのルーター。 |
| `app/templates/` | レイアウト・ページ・コンポーネント。 |
| `app/utils/` | 共通ユーティリティ。 |
| `app/tests/` | ユニット/API/E2E テスト。 |
| `assets/` / `builder/` | Tailwind ビルド資材。生成 CSS は編集禁止。 |
| `scripts/` | seeding・migration・testing の補助スクリプト。 |
| `rules/` | 本ドキュメントおよびコーディング/テスト規約。 |

## 禁止事項
- doc/実装/マイグレーション/生成物の同期漏れのままコミットしない。
- 未確認のまま既存データを破壊する変更を入れない（破壊的変更が必要なら別途合意を取る）。
- 生成物（Tailwind CSS など）を直接編集しない。

これらを守り、ドキュメント・テスト・実装を常に同期させた状態で開発を進めてください。
