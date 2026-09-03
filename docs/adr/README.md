# Architecture Decision Records

ADRは、sokoraの重要なarchitecture decisionについて「なぜその選択をしたか」を残す。

現在の設定値、API一覧、運用手順、file配置の正本にはしない。それらは [docs/README.md](../README.md) のsource-of-truth mapに従う。主要な現行contract文書は`docs/`直下へ集約し、ADRだけをdecision historyとしてこのdirectoryへ残す。

## Status

- **Accepted**: 現在のarchitecture判断として有効。
- **Superseded**: 後続ADRで置き換え済み。現行contractの根拠には使わない。

## Records

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-authentication.md) | Superseded | Keycloak固定・server-side session等の初期認証案 |
| [0002](0002-authentication-runtime.md) | Accepted | provider-neutral OIDC + signed client-side session |
| [0003](0003-multi-replica-runtime.md) | Accepted | shared PostgreSQL + request-local derived state |
| [0004](0004-provider-neutral-oci-deployment.md) | Accepted | provider-neutral OCI image + deployment adapter boundary |

## ADRを追加する基準

次のように、実装だけでは採用理由やtrade-offが失われるdecisionを対象とする。

- system全体または複数componentへ影響する責務境界
- runtime / persistence / security / consistencyの重要な制約
- 複数の妥当な選択肢から1つを採用し、将来の変更判断にも影響するもの

個別endpoint、private helper、単純なfile移動、現在のenvironment variable一覧などはADRへ書かない。

既存decisionを変更する場合は、過去ADR本文を現行仕様へ書き換えず、必要なら新しいADRでsupersedeする。現在成立すべきcontractは対応するrequirements / runtime / operations documentを同じ変更で更新する。
