# 0005: Provider-neutral deployment without cloud-specific adapters

**Status:** Accepted

## Context

ADR 0004では共通OCI imageとprovider別deployment adapterを分離する方針を採用した。

その後、sokora自体がGCP/AWS/Azure等を個別supportし、provider別script / IaC / validationを継続保守する必要はないと判断した。application側に必要なのはportable runtime contractであり、cloud infrastructureのprovisioningではない。

## Decision

- production artifactはroot `Dockerfile`からbuildするprovider-neutral OCI image 1種類
- repositoryは特定cloud provider向けadapter / deploy script / IaC / support matrixを持たない
- runtime contractは`PORT`、`DATABASE_URL`、runtime config/secret、`/healthz`等のprovider-neutral interfaceに限定
- SQLiteはsingle-instance + durable filesystem
- external / managed PostgreSQLはstandard PostgreSQLとして接続
- registry、network、ingress/TLS、identity、secret store、managed DB provisioning、scalingはdeployment environment側の責務
- provider SDK / metadata service / provider abstractionをapplication coreへ追加しない
- closed-network Docker bundleは実際にrepositoryが提供するdistribution targetとして維持する

## Consequences

providerごとのcontrol-plane変更をsokoraの保守対象にせず、application/runtime contractへ集中できる。

generic deploymentは [Deployment](../deployment.md)、production runtimeは [Runtime](../runtime.md)、closed-network operationは [Closed-network deployment](../closed-deployment.md) を参照する。

## Supersedes

- [ADR 0004](0004-provider-neutral-oci-deployment.md)
