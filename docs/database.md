# Database

sokoraはSQLiteとPostgreSQLを同じSQLAlchemy model / Alembic migration chainで扱います。schemaの一次情報は`app/models/`と`scripts/migration/`です。

## Data model

```mermaid
erDiagram
    GROUPS ||--o{ USERS : contains
    USER_TYPES ||--o{ USERS : classifies
    USERS ||--o{ ATTENDANCE : has
    LOCATIONS ||--o{ ATTENDANCE : categorizes

    GROUPS {
        int id PK
        string name UK
        int order
    }
    USER_TYPES {
        int id PK
        string name UK
        int order
    }
    LOCATIONS {
        int id PK
        string name UK
        string category
        int order
    }
    USERS {
        string id PK
        string username UK
        int group_id FK
        int user_type_id FK
    }
    ATTENDANCE {
        int id PK
        string user_id FK
        date date
        int location_id FK
        string note
    }
    CUSTOM_HOLIDAYS {
        int id PK
        date date UK
        string name
    }
    AUTH_CONFIG {
        int id PK
        boolean oidc_enabled
        string oidc_issuer
        string oidc_client_id
        text oidc_client_secret_encrypted
        string oidc_scope
    }
```

主要constraint:

- `users.username`はunique
- `attendance(user_id, date)`はunique
- `custom_holidays.date`はunique
- `auth_config`は`id = 1`のsingleton
- userはgroup / user type、attendanceはuser / locationへFKを持つ

## Backends

| Backend | Usage | Replica |
| --- | --- | --- |
| SQLite | local / standalone / closed-network | 1 |
| PostgreSQL | external / managed DB、multi-replica | 1..N |

接続先のSSoTは`DATABASE_URL`です。未指定時は:

```text
sqlite:///data/sokora.db
```

PostgreSQL:

```text
postgresql://user:password@db.example:5432/sokora
postgresql://user:password@db.example:5432/sokora?sslmode=require
```

bare `postgresql://` / `postgres://` はPsycopg 3へ内部正規化します。managed PostgreSQLもstandard PostgreSQLとして接続し、provider SDKやDB proxy processをdata-access layerへ組み込みません。

deployment上の選択は [Deployment](deployment.md) を参照してください。

## Schema lifecycle

1. application startupでAlembicをheadまで適用
2. migration failureならstartupをabort
3. fresh file-backed SQLiteだけinitial seedを作成
4. PostgreSQL / in-memory SQLiteはauto-seedしない

PostgreSQLの同時startup migrationはadvisory lockで直列化します。既存revisionは履歴として変更せず、schema変更は新しいrevisionを追加します。

migrationは既存data conflictを任意に削除して通しません。解決が必要なconflictは明示的にfailureとして扱います。

## Transaction ownership

```mermaid
flowchart LR
    Adapter["Page / API adapter"] --> Service["Service / use case"]
    Service --> CRUD["CRUD / data access"]
    CRUD --> DB[("Database")]
```

write use caseのtransaction ownerは`app/services/`です。`app/crud/`はquery / flush等のdatabase operationを担当し、use case単位のcommit / rollbackを所有しません。

DB constraint raceはservice境界でapplication errorへ変換します。

## Shared state

multi-replicaではshared PostgreSQLを利用し、DB由来のmutable stateをprocess-global cacheやreplica-local fileへ共有状態として保持しません。

- custom holiday: request開始時にshared DBから取得
- editable OIDC config: shared DBの`auth_config`
- immutable holiday asset: 同一image内でprocess-local保持可

consistency semanticsは [ADR 0003](adr/0003-multi-replica-runtime.md) を参照してください。

## Backup and restore

file-backed SQLiteのadmin backup / restoreは [SQLite database management](sqlite-database-management.md) を参照してください。

PostgreSQL backup / restoreはDB運用基盤側で行い、application GUIでは扱いません。
