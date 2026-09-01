# 0003: Shared PostgreSQL + request-local derived state for multi-replica runtime

**Status:** Accepted

## 背景

portable PostgreSQL backend導入後も、application replicaごとにDB由来のmutable cacheを保持すると、replica Aでwriteした直後にreplica Bへrouteされたreadが古い状態を返し得る。attendance/calendarのprocess-local cacheとauthのfile-backed runtime stateは先行Issueで除去したが、custom holidayはbuild-time祝日cacheと同じmodule-global dictionaryへDB内容をmergeしていたため、writeを処理したprocessだけが更新される状態だった。

## 決定

- horizontal multi-replica runtimeは、全replicaが同じexternal PostgreSQL databaseを共有する構成で保証する。SQLiteはsingle-instance/standalone用途とし、複数replicaで同じSQLite fileを共有する構成はサポートしない。
- DB由来のattendance/calendar read resultはprocess-global cacheへ保持しない。各requestは共有DBから現在の状態を読む。
- 標準祝日はproduction imageへbuildされたimmutable assetとしてprocess-localに保持してよい。同一imageを実行するreplica間で内容が一致し、runtime writeでは変更されないためである。
- custom holidayはprocess-global cacheへ保持しない。holidayを描画するrequestの開始時に共有DBから読み、request-local `ContextVar` snapshotへ束縛する。既存calendar builderはそのrequest-local snapshotを標準祝日より優先して解決する。
- custom holiday writeは共有DBへのtransaction commitだけを行い、特定replicaのcache invalidationを必要としない。commit完了後に開始した別replicaのholiday-sensitive readは共有DBから新しい値を取得する。
- 認証設定はenvironment/secret injectionをSSoTとし、replica-local mutable fileを持たない。署名付きclient-side session cookieを全replicaで検証できるよう、`SOKORA_AUTH_SESSION_SECRET` と認証/OIDC設定はreplica間で同一値を注入する。
- PostgreSQL migrationは既存のadvisory lock contractで同時startupを直列化する。

## Consistency contract

- write transactionがcommitした後に開始したread requestは、どのreplicaへrouteされてもそのcommitted stateを観測する。
- write commit前から進行中のread requestは、そのrequestが取得したsnapshotを返し得る。linearizableな全request直列化は要求しない。
- application runtimeが共有状態として依存してよいのは共有DB、runtime-injected config/secret、同一OCI imageに含まれるimmutable assetである。replica-local filesystemやmodule-global mutable DB cacheは共有stateとして利用しない。

## 検証

CIのPostgreSQL jobで同じdatabaseを参照する2つのlive Uvicorn processを起動し、replica Aでcustom holiday/attendanceを書き込んだ後、replica Bのcalendar readがその内容を返すことをintegration testで検証する。

## 影響

- GCP/AWS/Azureのmanaged container deployment adapterは、external PostgreSQLと共通runtime secret/configを利用する場合に複数replicaを許可できる。
- SQLite deploymentは引き続きreplica数1を前提とする。
- Redis等のdistributed cache/invalidation基盤は現時点では不要。将来performance上の理由でcacheを導入する場合は、このconsistency contractを満たす共有cacheまたは明示的version/invalidation設計が必要になる。
