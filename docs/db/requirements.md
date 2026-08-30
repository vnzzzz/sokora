# DB 要件

SQLAlchemy モデル（`app/models/*.py`）を基準にしたデータ設計の要件です。API 側の操作は [API 要件](../api/requirements.md)、UI からの利用は [UI 要件](../ui/requirements.md) を参照してください。

## テーブル定義
- `groups`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。`users` から参照される。  
- `user_types`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。`users` から参照される。  
- `locations`：`id` (PK, int), `name` (unique, not null, index), `category` (nullable, index), `order` (int, nullable)。`attendance` から参照される。UI の色付けは `id` に基づき `ui_utils.get_location_color_classes` で決定。  
- `users`：`id` (PK, string), `username` (not null, index), `group_id` (FK → groups.id, not null), `user_type_id` (FK → user_types.id, not null)。勤怠は `attendance_records` リレーションで紐付く。  
- `attendance`：`id` (PK, int), `user_id` (FK → users.id, not null, index), `date` (Date, not null, index), `location_id` (FK → locations.id, not null), `note` (nullable)。ドメインルールとして「ユーザー + 日付で一意」を API で検証（DB 制約は未付与）。削除時は関連 UI をリフレッシュする前提。

## DB 接続設定
- DB 接続先の SSoT は環境変数 `DATABASE_URL` とする。application、CLI session、Alembic、container entrypoint は同じ値を参照する。
- 未指定時の既定値は `sqlite:///data/sokora.db` とし、従来の SQLite 構成を維持する。
- 設定層では SQLAlchemy が解釈できる任意の URL を受け取れる。ただし現時点で運用・CI でサポートする backend は SQLite とし、PostgreSQL の driver・backend 固有対応は #56 で扱う。
- `sqlite:///:memory:` は test/application 単位で同一 connection-backed DB を共有できるように扱う。

## 初期化とシーディング
- `app/db/session.initialize_database()` は `DATABASE_URL` から生成された database runtime を使って初期化する。
- 現時点では schema 初期化に `Base.metadata.create_all()` を残している。schema lifecycle を Alembic に一本化する変更は #54 で行うため、この互換経路を DB の恒久的な管理方式とはしない。
- file-backed SQLite では、対象 DB ファイルが存在しない場合だけ初期データをシードする。既存 DB ファイルには自動シードしない。
- in-memory SQLite および SQLite 以外の URL では自動シードしない。必要なデータ投入は呼び出し側または専用の seed 手順で明示的に行う。
- シード処理は `scripts/seeding/` を使用し、デフォルトで 60 日前/後まで勤怠データを投入する。グループ/社員種別/勤務地/ユーザーの初期データが API と UI の前提になる。
- Alembic migration も `DATABASE_URL` を参照する。既存の Alembic revision は履歴として変更せず、モデル変更時は新しい migration を追加する。
