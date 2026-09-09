# Documentation guide

このdirectoryは、sokoraの現在のcontractとarchitecture decisionを追跡する入口です。

文書を細かいdirectoryへ分割しすぎず、独立した履歴を持つADRと画像を除いて`docs/`直下へ置きます。実装詳細を文書へ複製せず、利用者・運用者・開発者が判断するために必要なcontract、制約、設計判断、操作入口を記載します。

## Source of truth map

| 文書 | 正本として扱う内容 |
| --- | --- |
| [requirements.md](requirements.md) | product全体とcross-cuttingなruntime/architecture要件 |
| [api.md](api.md) | JSON API contractとAPI/page adapterの責務境界 |
| [database.md](database.md) | data model、DB backend、schema lifecycle、transaction contract |
| [ui.md](ui.md) | SSR/HTMX UIの利用者向けbehaviorとpage adapter contract |
| [templates.md](templates.md) | Jinja template / static assetの配置と責務 |
| [deployment.md](deployment.md) | generic container配置、SQLite/PostgreSQL構成、deployment environment責務 |
| [runtime.md](runtime.md) | provider非依存production OCI image/runtime contract |
| [closed-deployment.md](closed-deployment.md) | 実装済みclosed-network Docker bundle / Compose / operator手順 |
| [sqlite-database-management.md](sqlite-database-management.md) | SQLite backup/restoreの管理操作とfailure recovery contract |
| [adr/](adr/) | 重要なarchitecture decisionと、その採用理由・trade-off |

## RequirementsとADRの責務

Requirementsは**現在成立させるcontract**を記載します。URL、設定、data model、runtime behavior、運用上の制約など、現在のsystemを利用・変更するときに必要な事項が対象です。

ADRは**なぜそのarchitectureを選んだか**を記録します。背景、制約、選択、trade-off、結果を扱い、現在値や詳細手順をrequirements/operationsから複製しません。現在のcontractが変わった場合は該当文書を更新し、architecture decision自体が変わる場合だけADRを追加またはsupersedeします。

## Deployment documentation

共通のproduction artifactはprovider非依存OCI imageです。[deployment.md](deployment.md) には、特定cloud providerのsupport状況ではなく、一般的なcontainer runtimeが満たす条件とSQLite / external PostgreSQLの構成判断を記載します。

provider別adapter、deploy script、IaC、support matrixはsokora repositoryでは管理しません。実装済みのclosed-network Docker deploymentだけはrepository-owned distribution targetとして、bundle / Compose / operator手順を [closed-deployment.md](closed-deployment.md) に維持します。

## 更新ルール

- 同じ仕様や手順を複数文書で独立に保守しない。
- READMEやindexには入口だけを置き、詳細contractを複製しない。
- codeを読めば分かるprivate helperや逐次処理は文書へ転記しない。
- codeだけでは失われる判断理由、制約、不変条件、resource lifecycleは実装近傍のdocstring/commentへ残す。
- public contract、利用方法、architecture上の重要事項が変わる場合は、実装と同じ変更単位で対応文書を更新する。
- 未実装・未確認の機能を実装済みとして断定しない。
- 古い説明を現行仕様のように残さない。過去のarchitecture decisionはADRのstatusで区別する。
