# 0004: Provider-neutral OCI image + deployment adapter boundary

**Status:** Accepted

## 背景

sokoraはlocal/closed環境だけでなく、GCP/AWS/Azureのmanaged container runtimeでも同じapplicationを実行できる構成を目指す。

providerごとにapplication code、Dockerfile、DB access、認証処理を分岐すると、runtime contractがproviderへ結合し、同じ機能を複数の実装で保守することになる。一方で、registry、network、identity、secret service、managed PostgreSQLへの接続方法、probe、scaling等はprovider固有である。

## 決定

- production artifactはroot `Dockerfile`から生成するprovider非依存OCI image 1種類とする。
- applicationのruntime inputは`PORT`、`DATABASE_URL`、`SOKORA_*`、`OIDC_*`等のprovider非依存environment/secret contractとする。
- SQLite/PostgreSQLの接続、Alembic migration、authentication、health check等のapplication behaviorは共通image/runtimeが所有する。
- provider固有のregistry、image delivery、service定義、network/ingress/TLS、workload identity、secret injection、managed PostgreSQL接続、probe、scaling、CLI/config/IaCはdeployment adapterが所有する。
- GCP/AWS/Azure固有SDK、metadata service、credential discovery処理をapplication coreやDB access層へ追加しない。managed PostgreSQLはapplicationから標準PostgreSQL接続として扱う。
- closed-network deploymentも別application imageを作らず、同じproduction imageをarchive/registry等で配送し、Compose/template/operator assetsをadapterとして提供する。
- provider固有adapterが未実装のtargetについて、一般的なvendor手順だけをもってsokoraのdeploy support済みとは扱わない。再現可能なadapterとvalidationを各provider Issueで確立する。

## 結果

- applicationとproduction imageの変更をproviderごとに重複させずに済む。
- provider adapterは共通runtime contractを前提に独立して追加・変更できる。
- provider追加のためだけにapplicationへSDKや抽象化layerを追加しない。
- 共通CIはOCI runtime contractを検証し、provider固有のdeploy可能性は各adapterのvalidationで別途確認する。
- 現在のclosed-network adapterはこのboundaryに従う。GCP/AWS/Azure adapterは #57 / #70 / #71 で実装する。

## 関連文書

- [Deployment guide](../deployment.md)
- [Production container runtime contract](../runtime.md)
- [ADR 0003: multi-replica runtime](0003-multi-replica-runtime.md)
