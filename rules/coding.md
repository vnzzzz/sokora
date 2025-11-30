# コーディングガイドライン

本ドキュメントは `rules/development.md`（開発運用ルール）と `rules/testing.md`（テスト戦略）とセットで参照してください。

## 命名規則
- PEP 8 を基本に、関数・変数は `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE_CASE`。
- 勤怠ドメインの語彙（例: `attendance_type`, `working_location`, `calendar_month`）を優先し、抽象的な名前や不明瞭な略語は避ける。
- テンプレートや静的ファイルも役割が伝わるスラッグで命名し、`layout/base.html` → `templates/pages/*` → `templates/components/partials/*` の階層を崩さない。
- Alembic バージョンやスクリプトは目的が分かる短いスラッグを付与する。

## コメント / TODO
- 自明でない前提・制約・副作用だけを短く補足する。逐語的な説明は避ける。
- TODO は `# TODO(name): [ ] ...` の形式で、やることをチェックボックスで明示する。
- ドキュメント（README / docs / rules など）を更新する際は背景や判断理由まで日本語で残し、後から読んでも意図を推測させない。

## 責務分離
- **models**: SQLAlchemy モデル。Alembic と整合させる。
- **schemas**: Pydantic スキーマ（API 入出力）。
- **crud**: DB アクセスのみを担当。ビジネスロジックは持たない。
- **services**: ユースケース実装。複数 CRUD やユーティリティを組み合わせる。
- **routers/api/v1**: JSON API ルーター。入力バリデーションとサービス呼び出しに専念する。
- **routers/pages**: HTML ルーター。テンプレート用のコンテキスト組み立てと HTMX/Alpine エンドポイント。
- **templates**: レイアウト・ページ・共通部品を分割し、既存コンポーネントを優先して再利用する。
- **utils**: ドメイン非依存の共通処理。サービスから呼び出す。

## スタイルと型
- `black` / `isort` / `ruff` を通し、mypy の型エラーを残さない。
- すべての関数・メソッドに型ヒントを付け、返り値 `None` も明示する。
- DB セッションは依存注入やコンテキストマネージャで寿命を管理し、グローバルな共有セッションを避ける。

## エラーハンドリング
- サービスではドメイン例外を定義するか既存例外を使い、API ルーターで HTTP ステータスに正規化する。
- DB の一意制約違反や存在しない行は明示的に扱い、HTTP では `400/404/409/500` などにマッピングする。
- ログは境界層で1回にとどめ、同じ情報を重複記録しない。

## テンプレート / UI
- `layout/base.html` を起点に、ページは `templates/pages/`、共有部品は `templates/components/partials/` に追加する。
- Tailwind 生成物（`assets/css/main.css`）は直接編集せず、必要なスタイルはクラスを組み合わせる。
- HTMX/Alpine の既存パターン（スワップ先やトリガー、`hx-target` 等）に揃え、新規 JS を入れる場合は理由をコメントで残す。

## 設定 / 環境
- 設定値は `app/core/config.py` から読み、環境変数名の互換性を壊さない。
- 秘密情報は `.env` にのみ置き、`.env.sample` にはサンプル値だけを追加する。

これらを守り、レイヤー間の責務とドキュメントの整合性を維持したまま実装してください。
