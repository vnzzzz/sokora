# DB 要件

SQLAlchemy モデル（`app/models/*.py`）を基準にしたデータ設計の要件を記載する。

## モデル
- `groups`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。ユーザー所属を表す。
- `user_types`：`id` (PK, int), `name` (unique, not null, index), `order` (int, nullable)。社員種別を表す。
- `locations`：`id` (PK, int), `name` (unique, not null, index), `category` (nullable, index), `order` (int, nullable)。`attendance` から参照される。UI の色付けは `id` に基づき `ui_utils.get_location_color_classes` で決定。  
- `users`：`id` (PK, string), `username` (not null, index), `group_id` (FK → groups.id, not null), `user_type_id` (FK → user_types.id, not null)。勤怠は `attendance_records` リレーションで紐付く。  
- `attendance`：`id` (PK, int), `user_id` (FK → users.id, not null), `date` (Date, not null, index), `location_id` (FK → locations.id, not null), `note` (nullable)。`UNIQUE(user_id, date)` (`uq_attendance_user_date`) により「ユーザー + 日付で一意」を DB レベルで保証する。削除時は関連 UI をリフレッシュする前提。

## DB 接続設定
- DB 接続先の SSoT は環境変数 `DATABASE_URL` とする。application、CLI session、Alembic、container runtime は同じ値を参照する。
- サポートする backend は SQLite と PostgreSQL とする。
- 未指定時の既定値は `sqlite:///data/sokora.db` とし、local/閉域の従来構成を維持する。
- PostgreSQL は標準的な `postgresql://user:password@host:port/database` URL を application contract とする。bare `postgresql://` / `postgres://` は DB 層で Psycopg 3 (`postgresql+psycopg`) へ正規化する。SQLAlchemy driverを明示した `postgresql+...://` URL は呼び出し側の指定を維持する。
- TLS 等の PostgreSQL 接続オプションは URL query（例: `?sslmode=require`）として渡せる。secret を image や source code へ埋め込まない。
- Cloud SQL for PostgreSQL、Amazon RDS/Aurora PostgreSQL、Azure Database for PostgreSQL 等でも application は標準 PostgreSQL 接続情報だけを受け取る。provider 固有 SDK、metadata service、identity 処理、socket/proxy 起動処理を DB access 層へ追加しない。
- SQLite 固有設定は DB runtime factory に閉じ込める。SQLite runtime は `check_same_thread=False`、memory DB 用 `StaticPool`、すべての connection で `PRAGMA foreign_keys=ON` を適用する。これらを PostgreSQL engine へ適用しない。
- `sqlite:///:memory:` は test/application 単位で同一 connection-backed DB を共有できるように扱う。

## Schema lifecycle
- schema lifecycle の SSoT は Alembic とし、application runtime から `Base.metadata.create_all()` で production schema を生成しない。
- SQLite/PostgreSQL とも application startup の `initialize_database()` で Alembic head まで migration する。同じ schema revision chain を利用し、backend ごとに schema 定義を分岐しない。
- application startup の `initialize_database()` は application-scoped `DatabaseRuntime` の connection を使って `alembic upgrade head` 相当の migration を実行する。そのため in-memory SQLite でも request と migration が同じ connection-backed DB を利用する。
- PostgreSQL の online migration は transaction-level advisory lock で sokora の migration process 間を直列化する。lock は schema inspection から revision/version table 更新までを含む outer transaction と同じ寿命を持ち、commit/rollback時に自動解放する。
- migration に失敗した場合は application startup を失敗させ、DB schema が Alembic head でない状態で service を開始しない。
- 管理者が migration だけを明示実行する場合は `make migrate`（`alembic upgrade head`）を使用する。checkout directory に依存せず実行できることを contract とする。
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
- PostgreSQL および in-memory SQLite は自動シードしない。managed/external PostgreSQL の初期データ投入を application startup の暗黙処理にせず、必要なら専用の seed/import 手順から明示実行する。
- シード処理は `scripts/seeding/` を使用し、SQLite の初回ローカル運用ではデフォルトで 60 日前/後まで勤怠データを投入する。グループ/社員種別/勤務地/ユーザーの初期データが API と UI の前提になる。

## Backend integration test
- 通常の test/E2E suite は SQLite を継続利用し、既存 local/閉域 contract の回帰を検出する。
- CI は real PostgreSQL service に対して、bare `postgresql://` URL、同時startup migration、`make migrate` idempotence、application startup、Alembic head、master CRUD、user/attendance の主要 relational CRUD、`UNIQUE(user_id, date)` の重複拒否を検証する。
- PostgreSQL integration test は provider emulator ではなく PostgreSQL server を直接使用する。cloud provider 固有の network/identity 接続は deployment adapter 側で別途検証する。
