# Architecture Decision Records

ADRは、重要なarchitecture decisionの理由とtrade-offを記録します。

## Records

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-authentication.md) | Superseded | Keycloak固定 + server-side sessionの初期認証案 |
| [0002](0002-authentication-runtime.md) | Accepted | provider-neutral OIDC + signed session + shared DB OIDC config |
| [0003](0003-multi-replica-runtime.md) | Accepted | shared PostgreSQL + request-local derived state |
| [0004](0004-provider-neutral-oci-deployment.md) | Superseded | provider-neutral image + cloud adapter boundary |
| [0005](0005-provider-neutral-deployment-contract.md) | Accepted | provider-neutral deployment without cloud-specific adapters |

## Status

- **Accepted**: 現在のarchitecture decision
- **Superseded**: 後続ADRで置き換え済み。historical contextとしてのみ参照

