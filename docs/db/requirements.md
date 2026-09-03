# DB requirements

この文書は、sokoraのdata model、DB backend、schema lifecycle、transaction contractのSSoTとする。private helperやSQLAlchemy内部実装の逐次処理は記載しない。

## Data model

SQLAlchemy model (`app/models/`) とAlembic revisionがschemaの一次情報である。

- `groups`: `id` (PK), `name` (unique, not null), `order` (nullable)。ユーザー所属グループ。
- `user_types`: `id` (PK), `name` (unique, not null), `order` (nullable)。社員種別。
- `locations`: `id` (PK), `name` (unique, not null), `category` (nullable), `order` (nullable)。勤怠種別/勤務場所。
- `users`: `id` (string PK), `username` (not null), `group_id` (FK → `groups.id`), `user_type_id` (FK → `user_types.id`)。
- `attendance`: `id` (PK), `user_id` (FK → `users.id`), `date` (Date), `location_id` (FK → `locations.id`), `note` (nullable)。`UNIQUE(user_id, date)`で1ユーザー1日1レコードを保証する。
- `custom_holidays`: `id` (PK), `date` (Date, unique, not null), `name` (not null), `created_at`, `updated_at`。画面から追加する祝日を保持する。

DB constraintを最終的な整合性保証とし、application側の事前チェックは利用者向けerrorを早く返すために併用する。

## Database URL and supported backends

- DB接続先のSSoTは`DATABASE_URL`。
- supported backendはSQLiteとPostgreSQL。
- 未指定時は`sqlite:///data/sokora.db`。
- PostgreSQL application contractは標準的な`postgresql://user:password@host:port/database` URL。bare `postgresql://` / `postgres://` はPsycopg 3へ内部正規化する。
- TLS等のPostgreSQL connection optionはURL queryで渡せる。credentialをsource/imageへ埋め込まない。
- Cloud SQL for PostgreSQL、Amazon RDS/Aurora PostgreSQL、Azure Database for PostgreSQL等もapplicationからは標準PostgreSQL接続として扱う。provider SDK、metadata service、proxy processの起動をDB access層へ持ち込まない。

SQLite固有のconnection設定はDB runtimeへ閉じ込め、PostgreSQLへ適用しない。`sqlite:///:memory:`はtest/application単位で同一connection-backed DBを共有できるように扱う。

## Runtime topology

- file-backed SQLiteはsingle-instance runtime用。複数application replicaから同じSQLite fileを共有しない。
- horizontal multi-replicaはshared external PostgreSQLを利用する。
- DB由来のmutable read stateをprocess-global cacheへ共有状態として保持しない。
- custom holidayはrequest開始時に共有DBから読み、request-local snapshotとしてcalendar renderingへ渡す。multi-replica consistencyの詳細は [ADR 0003](../adr/0003-multi-replica-runtime.md) を参照する。

## Schema lifecycle

- schema lifecycleのSSoTはAlembic。production schemaを`Base.metadata.create_all()`で生成しない。
- SQLite/PostgreSQLともapplication startupでAlembic headまでmigrationする。migration失敗時はstartupをabortする。
- PostgreSQLのonline migrationはadvisory lockでsokora migration process間を直列化する。
- explicit migrationは`make migrate`を利用する。
- 既存Alembic revisionは履歴として変更せず、新しいmodel/schema変更はcurrent headへrevisionを追加する。
- pristine DBと、Alembic導入前のsupported SQLite DBを同じrevision chainへ移行できるようbaseline/adoption contractを維持する。
- `uq_attendance_user_date`追加時のように既存data conflictがある場合、migrationは任意にdataを削除せず明示的に失敗させる。

## Transaction ownership

- `app/crud/` のwriteはdatabase operationのstaging/flushを担当し、use case単位の`commit()` / `rollback()`を所有しない。
- write transaction ownerは`app/services/`。
- 複数tableを更新するuse caseは同一transactionで完結させ、一部だけをcommitしない。
- concurrent writeでDB constraintに競合した`IntegrityError`はservice境界でapplication errorへ変換し、adapterからDB例外文字列を直接公開しない。

## Initialization and seed

- migrationとseedは別責務。
- startupはmigration完了後、fresh file-backed SQLiteの場合だけinitial seedを作成する。
- PostgreSQLとin-memory SQLiteはstartupで自動seedしない。
- seed sourceは`scripts/seeding/`。

## SQLite backup / restore

file-backed SQLiteではadmin UI `/admin/database`からconsistent backup/restoreを利用できる。

- live DB fileの単純copy/overwriteは行わない。
- restore candidateはSQLite integrity、foreign key、current Alembic revision、current schema compatibilityを事前検証する。
- restoreはmigration手段ではなく、現在のapplication versionでそのまま利用できるDBだけを対象とする。
- PostgreSQLとin-memory SQLiteではfile backup/restore UIを無効化する。
- replacement/recoveryはrequest session drainとfail-closed boundaryを含む。

操作・failure recoveryの正本は [SQLite database management](../operations/sqlite-database-management.md) を参照する。

## Validation

通常test/E2EはSQLite contractを検証する。CIのPostgreSQL jobはreal PostgreSQLに対してmigration/startup、主要CRUD、constraint、multi-replica consistency、production image connectionを検証する。

provider固有のnetwork/identity/managed DB接続はDB contractではなくdeployment adapterの責務とする。
