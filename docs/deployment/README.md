# Deployment guide

sokoraのproduction deploymentは、root `Dockerfile`から生成する同一のprovider非依存OCI imageを共通artifactとし、環境差分をdeployment adapterへ分離する。

共通runtime contractは [runtime.md](runtime.md)、この判断の背景は [ADR 0004](../adr/0004-provider-neutral-oci-deployment.md) を参照する。

## Support status

| Target | Status | Entry point |
| --- | --- | --- |
| Closed network | Implemented | [closed.md](closed.md) |
| GCP Cloud Run | Planned / #57 | #57でadapterと再現可能なdeploy手順を実装する |
| AWS managed container | Planned / #70 | #70で推奨targetとadapterを実装する |
| Azure managed container | Planned / #71 | #71で推奨targetとadapterを実装する |

未実装targetについては、providerの一般的な手順をsokoraの正式なdeploy手順として先に固定しない。各Issueで実際のadapter、validation、運用境界が確定した時点でprovider別documentを追加する。

## Common boundary

application/runtimeが所有するもの:

- production OCI imageとcontainer entrypoint
- `PORT` / `DATABASE_URL` / `SOKORA_*` / `OIDC_*` 等のruntime input contract
- SQLite/PostgreSQLのapplication-level DB contract
- `/healthz`
- Alembicによるschema lifecycle

provider adapterが所有するもの:

- image registry / image delivery
- service/container platform設定
- network / ingress / TLS
- secret injection / workload identity
- external PostgreSQLへの接続方法
- platform probe / scaling設定
- provider固有CLI、config、IaC

application coreやDB access層へGCP/AWS/Azure固有SDKやmetadata service依存を追加しない。provider側のmanaged PostgreSQLもapplicationからは標準PostgreSQL接続として扱う。

## Database selection

- SQLiteはsingle-instanceのlocal/standalone/closed用途を対象とする。複数replicaから同じSQLite fileを共有しない。
- horizontal multi-replica runtimeはshared external PostgreSQLを利用する。共有状態contractは [ADR 0003](../adr/0003-multi-replica-runtime.md) を参照する。

## Validation boundary

共通runtime CIはproduction image、PostgreSQL contract、proxy、health、artifact boundaryを検証する。

provider固有adapterを追加するIssueでは、共通CIだけでdeploy可能とみなさず、そのproviderで必要なbuild/deploy/configuration boundaryを別途検証する。外部cloud環境を自動検証できない場合は、その未確認範囲をoperator actionとして明示する。
