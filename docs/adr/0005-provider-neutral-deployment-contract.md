# 0005: Provider-neutral deployment contract without cloud-specific adapters

**Status:** Accepted

## 背景

ADR 0004では、provider非依存OCI imageとprovider別deployment adapterを分離し、将来GCP/AWS/Azure向けadapterを追加する方針を採用した。

その後、sokoraとして各cloud providerを個別にsupportする必要はなく、providerごとのdeploy script、IaC、validationを長期保守する価値も低いと判断した。一方、root Dockerfileから生成する共通OCI image、SQLite/PostgreSQLのruntime contract、閉域Docker deploymentは既に有効な境界として成立している。

provider固有adapterを持たずに、一般的なcontainer runtimeが満たす条件とDB構成の考え方だけを文書化すれば、applicationのportable runtime contractを維持しながら保守対象を増やさずに済む。

## 決定

- production artifactはroot `Dockerfile`から生成するprovider非依存OCI image 1種類とする。
- sokora repositoryは、特定cloud provider向けのdeploy adapter、deploy script、IaC、support matrixを提供しない。
- repositoryが定義するdeployment contractは、OCI image、`PORT`、runtime environment/secret、`DATABASE_URL`、`/healthz`、DB topology等のprovider非依存部分に限定する。
- SQLiteはsingle-instanceとし、`/app/data`をSQLite file semanticsを満たすdurable filesystemへmountする。
- external / managed PostgreSQLは標準PostgreSQL接続URLとして扱い、provider固有SDKやDB proxy processをapplication/DB access層へ組み込まない。
- registry、container service、network、ingress/TLS、identity、secret store、managed DBのprovisioning、provider固有CLI/IaCはdeployment environment側の責務とする。
- horizontal multi-replicaはshared external PostgreSQLと共通runtime secret/configを利用する既存contractを維持する。
- 実装済みclosed-network Docker deploymentはrepository-owned distribution targetとして維持する。bundle、Compose、operator guide、upgrade/rollback、validationは [closed-deployment.md](../closed-deployment.md) をSSoTとする。

## 結果

- cloud providerごとの実装・検証・更新をsokoraの継続保守対象にしない。
- application codeとproduction imageはdeployment先を認識しない。
- generic container platformへ配置するときの判断材料は [deployment.md](../deployment.md) に集約する。
- SQLiteを使える環境ではsingle-instance + durable filesystem、そうでない場合やmulti-replicaではexternal PostgreSQLという単純な構成判断を維持できる。
- 特定環境で追加設定が必要になった場合も、まずその環境のoperator側設定として扱い、sokora側のprovider abstractionを追加しない。
- ADR 0004の「provider別adapterを追加する」決定は本ADRでsupersedeする。

## 関連文書

- [Deployment guide](../deployment.md)
- [Production container runtime contract](../runtime.md)
- [Closed-network deployment](../closed-deployment.md)
- [ADR 0003: multi-replica runtime](0003-multi-replica-runtime.md)
- [ADR 0004: provider-neutral OCI image + deployment adapter boundary](0004-provider-neutral-oci-deployment.md)
