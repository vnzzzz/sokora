# 0002: Provider-neutral OIDC + signed client-side session + shared DB OIDC settings

**Status:** Accepted

## 背景

認証runtimeはprovider非依存かつmulti-replicaで一貫している必要がある。一般ユーザーは標準OIDCを利用し、管理者にはOIDC設定障害から独立したbreak-glass経路が必要である。

当初はOIDC client設定もenvironment / secret injectionをSSoTとしていたが、運用者がlocal admin画面からKeycloak等のissuer/client設定を変更し、全replicaへ即時反映できるshared configurationが必要になった。一方で、既存deploymentをDB migrationだけで突然無効化せず段階移行できなければならない。

## 決定

- 一般ユーザーの一次認証経路は標準OIDC Authorization Code flowとする。Keycloakは利用可能なOIDC providerの一つであり、provider固有endpoint pathをapplicationで組み立てない。
- OIDC clientはAuthlibを利用し、issuerのOpenID Provider Configurationからauthorization/token/JWKS/end-session metadataをdiscoveryする。state、nonce、ID token検証等のprotocol boundaryは維持する。
- sessionはStarlette `SessionMiddleware`のsigned client-side cookieとし、persistent cookieには最小identityだけを保持する。access token / refresh token / ID tokenは保存しない。
- authentication guard、session signing secret、local admin credentialはdeployment runtime secret/configをSSoTとする。
- local adminはbreak-glass経路としてOIDC DB設定から切り離す。`SOKORA_LOCAL_AUTH_ENABLED=true`かつusername/passwordが設定されている場合だけ有効とし、OIDC設定や暗号鍵の不備でlogin不能にしない。
- OIDC client設定はsingleton `auth_config` rowでshared DB管理へ移行する。
  - rowなし: legacy `OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` / `OIDC_SCOPES`を利用する。
  - rowあり + enabled: DBのissuer/client ID/encrypted client secret/scopeを利用する。
  - rowあり + disabled: OIDCを明示無効化し、legacy environmentへfallbackしない。
- `OIDC_REDIRECT_URL`とHTTP timeoutはdeployment固有runtime propertyとしてenvironmentへ残す。
- client secretはFernetで暗号化してDBへ保存する。暗号鍵`SOKORA_AUTH_CONFIG_ENCRYPTION_KEY`はDB/imageへ保存せず、全replicaへ同じruntime secretを注入する。暗号鍵不一致時はOIDCをfail-closedとし、legacy secretへfallbackしない。
- `/auth/settings`はlocal admin専用のeditable OIDC管理画面とする。source/state表示、enable/disable、issuer/client ID/scope、secret更新、unlink、standard discovery接続確認を提供する。OIDCをenabledで保存する場合はdiscovery取得とmetadata issuer一致を必須とし、失敗したcandidateを有効設定として永続化しない。
- 保存済みclient secretはHTML/form/sessionへ再表示しない。設定確認・validation errorへsecretを含めない。
- unlinkは`auth_config` rowを削除せずdisabled rowとして残す。row削除はlegacy fallbackを再開してしまうため、通常UI operationにはしない。
- DB由来OIDC設定をprocess-global mutable cacheへ保持しない。shared PostgreSQLを利用するmulti-replicaはrequestごとに同じDB stateを観測する。
- 認証後の`next`はsame-origin absolute pathだけに制限する。
- logoutはapplication sessionを必ず先に破棄する。`POST /auth/logout`の最初のresponseはshared DB / IdPへ依存せずauthenticated identityをcookieから除去し、OIDC sessionの場合だけ別requestでRP-Initiated Logoutをbest-effort実行する。shared DB unavailableやDB接続black-holeでもprovider logoutがapplication logout完了を遅延・失敗させない。

## 移行

既存deploymentはAlembic migrationで空の`auth_config` tableを追加するだけで、rowを自動作成しない。そのためupgrade直後は従来の`OIDC_*` runtime設定がそのまま有効である。

local adminが初めてOIDC設定を保存・無効化・unlinkした時点でsingleton rowが作成され、その後はDBがOIDC stateのSSoTとなる。legacy environmentへ戻すためにrowを自動削除する挙動は提供しない。

## 影響

- OIDC設定変更にapplication restartは不要で、shared DBを通じてreplica間へ反映される。
- session signing/local admin credential/DB secret暗号鍵は引き続きdeployment secret managementの責務である。
- DB backupには暗号化済みOIDC client secretが含まれる。復号鍵はbackup外で別管理する必要がある。
- Keycloak固有設定画面ではなく標準OIDC issuerを入力するUIとする。
- application全体の共有状態contractは [ADR 0003](0003-multi-replica-runtime.md) に従う。
- runtime/API/UI/data modelの詳細contractは [runtime.md](../runtime.md)、[api.md](../api.md)、[ui.md](../ui.md)、[database.md](../database.md) をSSoTとする。

## Supersedes

- [ADR 0001: Keycloak OIDC + ローカル管理者フォールバックの採用](0001-authentication.md)
