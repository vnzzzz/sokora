# DB 要件

SQLAlchemy モデル（`app/models/*.py`）を基準にしたデータ設計の要件です。API 側の操作は [API 要件](../api/requirements.md)、UI からの利用は [UI 要件](../ui/requirements.md) を参照してください。

## テーブル定義
- `groups`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。`users` から参照される。  
- `user_types`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。`users` から参照される。  
- `locations`：`id` (PK, int), `name` (unique, not null, index), `category` (nullable, index), `order` (int, nullable)。`attendance` から参照される。UI の色付けは `id` に基づき `ui_utils.get_location_color_classes` で決定。  
- `users`：`id` (PK, string), `username` (not null, index), `group_id` (FK → groups.id, not null), `user_type_id` (FK → user_types.id, not null)。勤怠は `attendance_records` リレーションで紐付く。  
- `attendance`：`id` (PK, int), `user_id` (FK → users.id, not null, index), `date` (Date, not null, index), `location_id` (FK → locations.id, not null), `note` (nullable)。ドメインルールとして「ユーザー + 日付で一意」を API で検証（DB 制約は未付与）。削除時は関連 UI をリフレッシュする前提。

## 初期化とシーディング
- `app/db/session.initialize_database()` が DB の存在確認と初期化を行う。SQLite（`data/sokora.db`）を前提とし、無い場合はテーブル作成 + シード実行。
- シードスクリプトは `scripts/seeding/`（デフォルトで 60 日前/後まで投入）。グループ/社員種別/勤怠種別/ユーザーの初期データが API と UI の前提になる。
- 既存の Alembic バージョンは保持すること。モデル変更時はマイグレーション追加が必須。
