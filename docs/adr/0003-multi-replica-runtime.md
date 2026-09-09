# 0003: Shared PostgreSQL + request-local derived state for multi-replica runtime

**Status:** Accepted

## Context

複数application replicaがDB由来のmutable stateをprocess-local cacheへ保持すると、writeを処理したreplicaと別replicaのreadで状態がずれる。

SQLite fileを複数replicaで共有する方式も、sokoraのruntime contractとして扱わない。

## Decision

- horizontal multi-replicaは全replicaが同じexternal PostgreSQLを共有する構成
- SQLiteはsingle-instance
- attendance、calendar、custom holiday、editable auth config等のDB由来mutable stateをprocess-global shared cacheへ保持しない
- requestで必要なderived stateはshared DBから取得し、request-localに扱う
- 同一imageに含まれるimmutable assetはprocess-localに保持してよい
- session secret等のruntime config / secretはreplica間で同じ値を注入する
- PostgreSQL startup migrationはadvisory lockで直列化する

## Consistency

write commit後に開始したreadは、どのreplicaでもshared PostgreSQLのcommitted stateを取得する。

通常readはPostgreSQLのREAD COMMITTEDを前提とし、1 request全体をsingle snapshotとしてlinearizableにすることまでは要求しない。複数queryでview modelを作る場合は、mixed committed stateを500やinvalid shapeへ変換しないprojection boundaryを持つ。

## Consequences

- distributed cache / invalidation infrastructureは現時点では不要
- future cacheを導入する場合、このconsistency contractを満たす共有cacheまたは明示的invalidation設計が必要
- multi-replica deploymentはshared PostgreSQLと共通runtime secretsを前提とする

current state modelは [Architecture](../architecture.md)、DB topologyは [Database](../database.md) を参照する。
