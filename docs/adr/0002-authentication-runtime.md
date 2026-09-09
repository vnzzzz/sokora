# 0002: Provider-neutral OIDC + signed session + shared DB OIDC configuration

**Status:** Accepted

## Context

sokoraは特定IdPへ依存せずstandard OIDCを利用し、multi-replicaでもsessionと認証設定を共有できる必要がある。一方、OIDC障害や設定不備から独立した管理経路も必要である。

初期設計ではKeycloak固定、server-side session、file-backed runtime toggleを想定していたが、provider-neutral runtimeとshared stateの方針に合わない。

## Decision

- 一般ユーザーの一次認証はstandard OIDC Authorization Code flow
- provider metadataはissuer discoveryから取得し、provider固有endpointをapplicationへ組み込まない
- sessionはsigned client-side cookieとし、persistent sessionへOIDC tokenを保存しない
- local adminはOIDCから独立したbreak-glass経路
- session signing secret、local admin credential、OIDC secret暗号鍵はruntime secret
- editable OIDC client configはshared DBのsingleton `auth_config`へ保存
- DB rowがないupgrade直後だけlegacy `OIDC_*` environmentを利用し、row作成後はDBをauthoritative sourceとする
- OIDC client secretはDBへ暗号化して保存し、暗号鍵はDB/imageと分離する
- DB由来OIDC configをprocess-global mutable cacheへ保持しない
- application logoutをprovider logoutより先に成立させる

## Consequences

- Keycloakを含むstandard OIDC providerを同じruntime contractで扱える
- OIDC設定変更はshared DBを通じてreplicaへ反映される
- session secret / encryption keyは全replicaで同じ値を管理する必要がある
- DB backupには暗号化済みOIDC secretが含まれるため、復号鍵はbackupと分離して保管する
- local admin credentialはOIDC設定障害時にも利用可能なruntime-only secretとして残る

current behavior / setting precedenceは [Authentication](../authentication.md) を参照する。

## Supersedes

- [ADR 0001](0001-authentication.md)
