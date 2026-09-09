# Documentation

sokoraの利用・開発・運用に必要な情報を、目的別に分けています。実装詳細を複数文書へ複製せず、各topicの正本へ集約します。

## Start here

| 目的 | 文書 |
| --- | --- |
| localで起動・開発する | [Getting started](getting-started.md) |
| 全体構成を理解する | [Architecture](architecture.md) |
| 認証を設定・運用する | [Authentication](authentication.md) |
| JSON APIを利用する | [API](api.md) |
| data model / migrationを確認する | [Database](database.md) |
| SSR / HTMX UIを変更する | [UI](ui.md) |
| production image/runtimeを理解する | [Runtime](runtime.md) |
| container環境へdeployする | [Deployment](deployment.md) |
| 閉域Dockerサーバーへdeployする | [Closed-network deployment](closed-deployment.md) |
| SQLiteをbackup / restoreする | [SQLite database management](sqlite-database-management.md) |
| 設計判断の背景を追う | [Architecture Decision Records](adr/README.md) |

## Document ownership

| Topic | Source of truth |
| --- | --- |
| application layer / state boundary | [architecture.md](architecture.md) |
| authentication / authorization / session | [authentication.md](authentication.md) |
| public JSON API | [api.md](api.md) + generated OpenAPI |
| schema / DB backend / transaction | [database.md](database.md) + SQLAlchemy/Alembic |
| browser UI / HTMX / template responsibility | [ui.md](ui.md) |
| production image / startup / health | [runtime.md](runtime.md) |
| deployment topology | [deployment.md](deployment.md) |
| closed-network operator workflow | [closed-deployment.md](closed-deployment.md) + bundled operator guide |
| architecture decision history | [adr/](adr/) |

現在の仕様は上記文書、設計判断の理由はADR、code-levelの詳細は実装を正本とします。過去の説明を現行仕様として残すための互換文書は置きません。
