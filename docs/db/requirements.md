# DB 要件

SQLAlchemy モデル（`app/models/*.py`）を基準にしたデータ設計の要件です。API 側の操作は [API 要件](../api/requirements.md)、UI からの利用は [UI 要件](../ui/requirements.md) を参照してください。

## テーブル定義
- `groups`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。`users` から参照される。  
- `user_types`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。`users` から参照される。  
- `locations`：`id` (PK, int), `name` (unique, not null, index), `category` (nullable, index), `order` (int, nullable)。`attendance` から参照される。UI の色付けは `id` に基づき `ui_utils.get_location_color_classes` で決定。  
- `users`：`id` (PK, string), `username` (not null, index), `group_id` (FK → groups.id, not null), `user_type_id` (FK → user_types.id, not null)。勤怠は `attendance_records` リレーションで紐付く。  
- `attendance`：`id` (PK, int), `user_id` (FK → users.id, not null), `date` (Date, not null, index), `location_id` (FK → locations.id, not null), `note` (nullable)。`UNIQUE(user_id, date)` (`uq_attendance_user_date`) により「ユーザー + 日付で一意」を DB レベルで保証する。削除時は関連 UI をリフレッシュする前提。

## DB 接続設定
- DB 接続先の SSoT は環境変数 `DATABASE_URL` とする。application、CLI session、Alembic、container entrypoint は同じ値を参照する。
- 未指定時の既定値は `sqlite:///data/sokora.db` とし、従来の SQLite 構成を維持する。
- 設定層では SQLAlchemy が解釈できる任意の URL を受け取れる。ただし現時点で運用・CI でサポートする backend は SQLite とし、PostgreSQL の driver・backend 固有対応は #56 で扱う。
- SQLite runtime はすべての connection で `PRAGMA foreign_keys=ON` を有効化し、model/migration で定義した FK を実際に強制する。
- `sqlite:///:memory:` は test/application 単位で同一 connection-backed DB を共有できるように扱う。

## Schema lifecycle
- schema lifecycle の SSoT は Alembic とし、application runtime から `Base.metadata.create_all()` で production schema を生成しない。
- application startup の `initialize_database()` は、application-scoped `DatabaseRuntime` の connection を使って `alembic upgrade head` 相当の migration を実行する。そのため in-memory SQLite でも request と migration が同じ connection-backed DB を利用する。
- migration に失敗した場合は application startup を失敗させ、DB schema が Alembic head でない状態で service を開始しない。
- 管理者が migration だけを明示実行する場合は `make migrate`（`alembic upgrade head`）を使用する。
- 既存の Alembic revision は履歴として変更しない。旧 revision は既存schemaへの差分から始まるため、#54 で追加した baseline revision が pristine DB の現行schemaを構築する。
- pristine DB と、#54 より前の `create_all()` で生成された現行schemaの unversioned DB は、immutable な旧 migration head を adoption point として Alembic 管理へ移行する。旧schemaの unversioned DB は従来の migration chain を通常どおり適用する。
- `uq_attendance_user_date` 追加 migration は既存 duplicate を任意に削除しない。重複が存在する DB は migration を明示的に失敗させ、データを確認・解消してから再実行する。
- 新しい model/schema 変更では既存 revision を編集せず、現在の Alembic head へ revision を追加する。

## Transaction と整合性
- `app/crud/` の write operation は persistence の staging と `flush()` までを担当し、`commit()` / `rollback()` を所有しない。
- write use case の transaction owner は `app/services/` とする。service は use case 全体を 1 transaction として commit し、途中失敗時は rollback する。
- ユーザー削除のような複数テーブル更新は、関連 `attendance` 削除と `users` 削除を同一 transaction で実行し、一部だけが確定しないようにする。
- application-side の事前重複・参照チェックは利用者向けエラーのために維持するが、concurrent write の最終整合性は DB の UNIQUE / FK 制約で保証する。
- DB constraint の race により発生した `IntegrityError` は service 境界で application error に変換し、adapter が DB 例外文字列を外部へ直接公開しない。

## 初期化とシーディング
- `app/db/session.migrate_database()` が schema migration、`seed_database()` が初期データ投入を担当し、schema変更とdata seedを別責務として扱う。
- `app/db/session.initialize_database()` は startup orchestration として、先に migration を完了してから必要な場合だけ seed を呼び出す。
- file-backed SQLite では、対象 DB ファイルが存在しない場合だけ初期データをシードする。既存 DB ファイルには自動シードしない。
- in-memory SQLite および SQLite 以外の URL では自動シードしない。必要なデータ投入は呼び出し側または専用の seed 手順で明示的に行う。
- シード処理は `scripts/seeding/` を使用し、デフォルトで 60 日前/後まで勤怠データを投入する。グループ/社員種別/勤務地/ユーザーの初期データが API と UI の前提になる。
