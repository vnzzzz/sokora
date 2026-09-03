# Documentation guide

このdirectoryは、sokoraの現在のcontractとarchitecture decisionを、責務ごとに追跡できる形で管理する。

実装詳細を文書へ複製せず、利用者・運用者・開発者が判断するために必要なcontract、制約、設計判断、操作入口を記載する。実装と文書が食い違う場合は、該当Issueの完了条件とmainの実装を確認し、正しいSSoTを同じ変更で更新する。

## Source of truth map

| 文書 | 正本として扱う内容 |
| --- | --- |
| [requirements.md](requirements.md) | product全体とcross-cuttingなruntime/architecture要件 |
| [api/requirements.md](api/requirements.md) | JSON API contractとAPI/page adapterの責務境界 |
| [db/requirements.md](db/requirements.md) | data model、DB backend、schema lifecycle、transaction contract |
| [ui/requirements.md](ui/requirements.md) | SSR/HTMX UIの利用者向けbehaviorとpage adapter contract |
| [ui/templates.md](ui/templates.md) | Jinja template / static assetの配置と責務 |
| [deployment/README.md](deployment/README.md) | deploymentの入口、providerごとの実装status、責務境界 |
| [deployment/runtime.md](deployment/runtime.md) | provider非依存production OCI image/runtime contract |
| [deployment/closed.md](deployment/closed.md) | 実装済みclosed-network deployment adapterと運用境界 |
| [operations/sqlite-database-management.md](operations/sqlite-database-management.md) | SQLite backup/restoreの管理操作とfailure recovery contract |
| [adr/](adr/) | 重要なarchitecture decisionと、その採用理由・trade-off |

## RequirementsとADRの責務

Requirementsは**現在成立させるcontract**を記載する。URL、設定、data model、runtime behavior、運用上の制約など、現在のsystemを利用・変更するときに必要な事項を対象とする。

ADRは**なぜそのarchitectureを選んだか**を記録する。背景、制約、選択、trade-off、結果を扱い、現在値や詳細手順をrequirements/operationsから複製しない。現在のcontractが変わった場合はrequirementsを更新し、architecture decision自体が変わる場合だけADRを追加またはsupersedeする。

## Deployment documentation

共通のproduction artifactはprovider非依存OCI imageである。provider固有差分はdeployment adapterへ閉じ込める。

現在、closed-network adapterは実装済み。GCP Cloud Run、AWS managed container、Azure managed containerはそれぞれ #57、#70、#71 で未実装のため、再現可能なdeploy手順が存在するものとしては記載しない。現在のstatusと将来の入口は [deployment/README.md](deployment/README.md) を参照する。

## 更新ルール

- 同じ仕様や手順を複数文書で独立に保守しない。
- READMEやindexには入口だけを置き、詳細contractを複製しない。
- codeを読めば分かるprivate helperや逐次処理は文書へ転記しない。
- public contract、利用方法、architecture上の重要事項が変わる場合は、実装と同じ変更単位で対応文書を更新する。
- 未実装・未確認の機能を実装済みとして断定しない。
- 古い説明を現行仕様のように残さない。過去のarchitecture decisionはADRのstatusで区別する。
