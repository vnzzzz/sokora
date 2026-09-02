# SQLite database management

`/admin/database` は、ファイルベースSQLiteで稼働するsokora向けの管理者専用backup/restore入口です。

## Access boundary

- `require_admin` を利用し、`role=admin` のsigned sessionだけを許可する。
- 現行のadmin identityはlocal admin loginで付与される。
- PostgreSQLおよびin-memory SQLiteではbackup/restore操作を無効化する。
- 操作結果はapplication logへactorと共に記録する。DB内容やsecretはlogへ出力しない。

## Backup contract

稼働中のDBファイルを直接copyしない。Python標準`sqlite3.Connection.backup()`で一時DBへconsistent snapshotを作成し、SQLite `integrity_check`後にdownloadする。

downloadしたDBは通常のSQLite fileであり、`-wal` / `-shm` sidecarを必要としない。

## Restore validation

uploadはlive DBと同じdirectoryのtemporary fileへstageし、live DBを変更する前に次をすべて確認する。

1. SQLite file header
2. `PRAGMA integrity_check`
3. `PRAGMA foreign_key_check`
4. `alembic_version` が現在のAlembic headと完全一致
5. table / column / foreign key / index / view / trigger schemaが稼働中DBと一致

revisionやschemaが古いDBをuploadしてapplication startup migrationへ暗黙に委ねることはしない。restoreは「現在のversionでそのまま利用できるDB」の置換操作に限定する。

## Restore transaction boundary

restore時はapplication DB runtimeをmaintenance modeへ切り替える。

1. 新しいrequest DB sessionの開始を停止
2. 既存request DB sessionがcloseするまで待機
3. live DBのconsistent rollback backupを作成
4. SQLAlchemy poolをdispose
5. 古い`-wal` / `-shm` / `-journal` sidecarを除去
6. staged DBを同一filesystem内で`os.replace()`してatomic replacement
7. engine / session factoryを再生成
8. Alembic revisionを再確認
9. 成功後にrequest DB sessionを再開

replacement後に失敗した場合は、maintenance modeを解除する前にpre-restore rollback backupから自動復旧を試みる。自動rollback自体が失敗した場合はservice再起動と運用backupからの手動復旧が必要。

## Closed deploymentとの関係

`deploy/closed` のupgrade/rollback手順で要求しているSQLite backup APIの考え方と同じです。GUI backupは日常運用向けですが、image/schema upgrade前の運用backupを置き換えるものではありません。schema-changing rollbackでは引き続きupgrade前backupを明示的に保持します。
