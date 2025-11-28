# Codex プロジェクトメモリ（sokora）

このドキュメントは、OpenAI Codex などのエージェントが **sokora** リポジトリで安全かつ一貫性のある変更を行うためのガイドです。

---

## 0. プロジェクト概要

- 名前: **sokora**
- 説明: 直感的なカレンダーインターフェースで勤怠種別（リモート / オフィスなど）を可視化する Web アプリケーション。
- 主な機能:
  - インタラクティブな月次カレンダー UI（リモート / オフィス勤務などの集計を含む）
  - 日別詳細やユーザーごとのスケジュール表示
- 技術スタック:
  - Python 3.13 / FastAPI / Jinja2
  - HTMX / Alpine.js（SSR + インタラクティブ UI）
  - SQLite + SQLAlchemy + Alembic
  - Poetry（依存管理）
  - pytest / pytest-asyncio / pytest-playwright（E2E） / mypy / ruff
  - Docker（devcontainer / 単体コンテナ運用想定）

---

## 1. 必須ルール（Codex 共通）

- **ファイル編集は `apply_patch` を基本とする。**
  - シェルコマンドによる大規模な置換・削除は避け、差分は最小限にとどめる。
- **既存ファイルを尊重し、ユーザーが加えた変更を巻き戻さない。**
  - 既存の意図が読み取りづらい場合は、コメントや docstring を追加して補う。
- **破壊的な Git 操作は禁止。**
  - `git reset --hard`, `git checkout -- <path>`, rebase など履歴を壊す操作は行わない。
- **必ず TDD で進める。**
  1. まず「落ちるテスト」を書く（または既存テストを更新する）。
  2. 最小限の実装でテストを通す。
  3. テストが緑になってから、リファクタリングを行う。
- **ディレクトリ責務を守る。**
  - models / schemas / crud / services / routers / templates / utils の役割を混在させない。
- **仕様・要件に関わる変更は、コードよりも先にドキュメントを補正する。**
  - 既存仕様とタスクの要件がぶつかる場合は、先にドキュメント側の意図を揃える。

---

## 2. 優先事項

- **UI・API・DB・テストの整合性を常に保つ。**
  - 勤怠の種別や集計ロジックを変更した場合、以下を必ず確認する:
    - モデル (`app/models/`)
    - スキーマ (`app/schemas/`)
    - CRUD / services (`app/crud/`, `app/services/`)
    - API ルーター (`app/routers/api/v1/`)
    - ページルーター + テンプレート (`app/routers/pages/`, `app/templates/`)
    - テスト (`app/tests/...`)
- **UI 仕様・テンプレート構造の一貫性を守る。**
  - `layout/base.html` を土台とし、`templates/pages/`・`templates/components/` の責務分割を維持する。
  - カレンダーやモーダルなど共通 UI パターンは `components/partials/` 以下の構造を踏襲する。
- **テストコードを「一次情報源」として扱う。**
  - 振る舞いや境界条件は、できる限りテスト側に明文化し、実装はテストを根拠に整える。

---

## 3. 触れてはいけない領域

以下は、ユーザーから明示的な指示がある場合を除き、変更しないこと。

- **インフラ・環境構成の根幹:**
  - ルートの `Dockerfile`
  - `.devcontainer/` 配下（devcontainer 内での基本挙動を変える変更）
  - CI / GitHub Actions（存在する場合）
- **資格情報・秘密情報:**
  - `.env` / 本番向けのシークレット値をコードにハードコードしない。
  - `.env.sample` は、サンプル値の更新や新規キーの追加のみ行い、実運用値は書かない。
- **生成物の直接編集:**
  - Tailwind の生成 CSS（`assets/css/main.css`）等、ビルド成果物に相当するファイルを直接編集しない。
  - 変更が必要な場合は `builder/` 配下のソースを更新し、ビルドフローを通す。

---

## 4. 作業上の取り決め

- **TODO の書き方:**
  - `# TODO(username): [ ] やること` のように、担当とチェックボックスを明記する（担当名は分からなければ `TODO(sokora-team)` など）。
- **前提・制約の明示:**
  - 不確実な仕様や仮定で実装した場合は、その旨をコメントか docstring に記載する。
- **ディレクトリの不在や想定と異なる構成を見つけた場合:**
  - 推測で新しい構造を乱立させず、既存のパターンを優先する。
- **フォーマットと静的解析:**
  - 変更箇所は `black` / `isort` / `ruff` / `mypy` で警告が出ないように整える。
  - プロジェクト全体のフォーマットを一括で変えるような大変更は行わない。

---

## 5. sokora プロジェクト固有の構造

### 5.1 アプリケーション構成

- `app/main.py`
  - FastAPI アプリケーションのエントリポイント。
  - すべてのルーター・テンプレート・静的ファイルの設定をここで集約する。

- `app/core/`
  - `config.py`: 設定値（環境変数、DB URL、アプリ設定など）を管理するモジュール。
  - 設定名・環境変数名は互換性が重要なため、変更が必要なときは慎重に検討する。

- `app/db/`
  - `session.py`: SQLAlchemy エンジン / セッションの生成。

- `app/models/`
  - SQLAlchemy モデル定義。
  - Alembic マイグレーションと整合していることが前提。

- `app/schemas/`
  - Pydantic モデル（API 入出力のスキーマ）。
  - `models` との対応を意識しつつ、API 表現として必要な形に整える。

- `app/crud/`
  - DB アクセスを担当する CRUD レイヤー。
  - 生のクエリはここに集約し、ビジネスロジックは `services` に寄せる。

- `app/services/`
  - 勤怠・勤務場所・ユーザーなど、ドメインごとのユースケース実装。
  - ルーターから呼び出され、CRUD / utils を組み合わせて処理する。

- `app/routers/api/v1/`
  - JSON API のルーター。
  - ファイルごとにリソース（attendance / user / location / group / user_type など）を担当する。

- `app/routers/pages/`
  - HTML ページのルーター。
  - テンプレートと HTMX / Alpine.js を組み合わせ、画面単位の振る舞いを定義する。

- `app/templates/`
  - `layout/base.html`: 全ページ共通のレイアウト。
  - `pages/*.html`: トップ / カレンダー / 勤怠登録 / ユーザー・組織・ロケーション管理などの画面。
  - `components/`: 行テンプレート・モーダル・ヘッダ・サイドバーなどの共通コンポーネント。
  - テンプレートは **layout → pages → components/partials** の構造を守る。

- `app/static/`
  - `css/`, `js/`, `favicon.ico` などの静的ファイル。
  - Tailwind 生成 CSS（`assets/css/main.css`）や JS ライブラリ（htmx / Alpine）はコンテナ内 `/app/assets` に配置されることを前提とする。

- `app/utils/`
  - `calendar_utils.py`: カレンダー表示・集計ロジック。
  - `csv_utils.py`: CSV に関するユーティリティ。
  - `holiday_cache.py`: 祝日キャッシュ機構。
  - `ui_utils.py`: UI 共通処理。
  - ドメインに強く依存しない共通ロジックを配置する。

- `app/tests/`
  - `conftest.py`: テスト設定・共通 fixture。
  - `crud/`, `routers/`, `services/`, `utils/`: ユニットテスト・API テスト。
  - `e2e/`: E2E テスト（pytest-playwright を利用）。
  - `tests/utils/`: DB チェック・クリーンアップ用の補助スクリプト。

### 5.2 ルート直下の構成

- `Dockerfile`
  - 本番用のシングルコンテナ定義。
  - Tailwind CSS ビルド（builder ステージ）・祝日キャッシュ生成・htmx / Alpine ダウンロードを含む。

- `pyproject.toml`
  - Poetry 設定および依存ライブラリ定義。
  - `tool.poetry.group.dev.dependencies` に開発ツール（black, isort, mypy, pytest, pytest-cov, pytest-asyncio, ruff, pytest-playwright, alembic）が含まれる。

- `builder/`
  - Tailwind CSS ビルド用。
  - `input.css`, `tailwind.config.js`, `postcss.config.js`, `package.json` を含む。

- `data/`
  - `sokora.db`: SQLite データベースファイル。`init_db()`（シーダー含む）が存在しない場合に作成する。
  - アプリ起動時（`make run` / `make docker-run`）に `data/sokora.db` が無い場合は自動でテーブル作成とシーディング（60日/60日分）を実行し、旧 `data/sokora.sqlite` があれば `sokora.db` にリネームして利用する。
  - Docker ビルド時 (`make build` / `make docker-build`) も DB が無ければ初期化＋シーディングを実行し、ベースイメージに DB を含める。ビルド成果物は `/app/seed/sokora.db` にコピーされ、エントリポイントでホストマウントされた `data/` に複製される。
  - `data/.gitkeep` のみがコミットされており、DB は実行時に生成。

- `docs/`
  - ドキュメント類。UI テンプレート仕様などがここに追加される。

- `scripts/`
  - `build_holiday_cache.py`: 祝日キャッシュのビルドスクリプト。
  - `migration/`: Alembic 設定とマイグレーションファイル。
  - `seeding/`: 初期データ投入スクリプト（`run_seeder.sh` で `data_seeder.py` を実行）。
  - `testing/run_test.sh`: テスト一括実行スクリプト。

---

## 6. 開発・起動方法

### 6.1 基本コマンド（Makefile）

- 依存関係インストール（poetry + builder npm）: `make install`
- 開発サーバー起動: `make run`（Tailwind など dev 資材を準備して `uvicorn` をリロード付きで起動）
- シーディング: `make seed`（後述のデフォルトデータを自動投入）
- 祝日キャッシュ: `make holiday-cache`
- Tailwind ビルド: `make assets`
- テスト一括実行: `make test`

### 6.2 Dev Container / Docker 補足

- devcontainer 起動済みなら `make dev-shell` でアタッチできる（名前は `sokora-dev` を想定）。
- Docker イメージビルド: `make build`（本番用）、`make dev-build`（devcontainer 用）。
- 本番コンテナ起動補助: `make docker-run` / `make docker-stop`（`.env` を読む）。
- ローカルで直接動かす場合の最低限コマンド:

  ```bash
  poetry install --no-root
  poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

  Tailwind 生成物が必要なときは `make prepare-dev-assets` か `make assets` を実行する。

---

## 7. テスト戦略（TDD）

### 7.1 テスト実行の基本

標準テストフローは専用スクリプトで行う：

```bash
cd /app
./scripts/testing/run_test.sh
```

このスクリプトは次を行う：

1. **事前チェック・クリーンアップ**
   - `PYTHONPATH=/app` を設定。
   - `app/tests/utils/db_checker.py` で DB 状態を確認。
   - `app/tests/utils/data_cleanup.py` で残存テストデータを削除。
   - 再度 `db_checker.py` で確認。

2. **API・ユニットテスト**
   - `poetry run pytest -vv app/tests/routers/ app/tests/crud/ app/tests/services/ app/tests/utils/`
   - 失敗した場合は即終了。

3. **E2E テスト**
   - `poetry run pytest -vv app/tests/e2e/`
   - 失敗した場合は即終了。
   - E2E は `http://localhost:8000` でアプリが起動している前提。必要に応じて `make run` 等でサーバーを立ち上げてから実行する。

4. **事後検証**
   - 再度 `db_checker` でテスト後の DB 状態を確認し、必要に応じて `data_cleanup.py` を実行。

### 7.2 TDD の適用方針

- 新しい機能追加 / 仕様変更では以下を徹底する：

  1. 受け入れテストから着手する。
     - API 変更なら `app/tests/routers/api/v1/` のテストを追加・更新。
     - 画面変更なら `app/tests/e2e/` や `app/tests/routers/pages/` にテストを追加。
  2. サービス・ユーティリティのテストを書く。
     - `app/tests/services/` や `app/tests/utils/` を更新。
  3. 必要に応じて CRUD / モデルのテストを追加する。
  4. すべてのテストが緑になるまで実装を小さく進める。

- 既存テストの削除は **極力避ける**。
  - 振る舞いを変える必要がある場合は、テストの期待値を更新し、変更理由をコメントで残す。

---

## 8. DB・マイグレーション・シーディング

- データベース:
- SQLite: `data/sokora.db`
  - `app/db/session.init_db()` が存在しない場合にテーブルを作成する。`make seed` でも自動実行。

- マイグレーション:
  - Alembic 設定とバージョンファイルは `scripts/migration/alembic/` に存在。
  - 一般的な操作例（参考）:

    ```bash
    cd /app
    alembic -c scripts/migration/alembic.ini upgrade head
    ```

- シーディング:
  - スクリプト: `scripts/seeding/data_seeder.py`
  - シェル: `scripts/seeding/run_seeder.sh [days_back] [days_forward]`（デフォルト 60/60）。`make seed` は `SEED_DAYS_BACK` / `SEED_DAYS_FORWARD` を渡す。
  - 2025-11 時点の動作: DB が空なら以下を自動投入後、勤怠をシードする。
    - グループ3件（開発部/営業部/バックオフィス）
    - 社員種別3件（正社員/契約社員/インターン）
    - 勤怠種別4件（東京オフィス/大阪オフィス/テレワーク/夜勤）
    - ユーザー5件（ID: U001〜U005）
  - 既存の勤怠 (user_id + 日付) がある日は重複を避け、それ以外の日付範囲に追加する。

**Codex への指示:**

- 既存の Alembic バージョンファイルを破壊的に書き換えない。
- モデル (`app/models/`) を変更した際は、対応するマイグレーションを追加する。
- シーディングロジックは、既存のデータとの互換性を意識して変更する。

---

## 9. コーディング規約と品質ツール

- フォーマッタ:
  - `black` (`line-length = 88`, `target-version = py313`)
  - `isort`（profile = `black`）

- 静的解析:
  - `mypy`
    - `python_version = 3.13`
    - `disallow_untyped_defs = true`
    - `disallow_incomplete_defs = true`
  - `ruff`

- pytest 設定:
  - `asyncio_mode = "auto"`
  - DeprecationWarning など一部 warning を無視する設定あり。

**推奨コマンド例（参考）:**

```bash
# フォーマット
poetry run black app
poetry run isort app

# 静的解析
poetry run mypy app
poetry run ruff check app

# テスト
./scripts/testing/run_test.sh
```

---

## 10. ドキュメントと同期のチェック

- 仕様変更や画面変更を行うときは、以下を意識する：

  1. README / docs/（テンプレート仕様など）が実装とズレていないか確認する。
  2. 仕様変更があれば、コードより先にドキュメントを更新する。
  3. 実装後に再度 README / docs/ と実際の挙動を見比べる。

- ドキュメントが不足していて、実装のほうが具体的な場合は：
  - テストケース・コメント・テンプレート名を通じて「事実としての仕様」を読み取り、必要に応じて docs に追記する。

---

## 11. まとめ（Codex への最重要ポイント）

1. `/app` をリポジトリルートとして扱うこと。
2. 既存のディレクトリ責務（models / schemas / crud / services / routers / templates / utils / tests）を崩さないこと。
3. すべての変更は TDD（テスト → 実装 → リファクタリング）の順番で行うこと。
4. Docker / devcontainer / インフラ関連は、明示的な指示がない限り手を入れないこと。
5. 仕様変更時はドキュメントとテストを一次情報源とし、コードと挙動をそれに揃えること。

この AGENTS.md は sokora 用の初版であり、今後の開発で気づいた点があれば適宜更新してよい。
