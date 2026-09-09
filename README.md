# sokora

![sokora](docs/images/image1.png)

勤怠種別と勤務場所をカレンダーで可視化・編集する、シンプルな勤怠管理Webアプリケーションです。

- 月次 / 週次カレンダーと日別勤怠
- ユーザー・グループ・勤怠種別・社員種別・祝日の管理
- CSV出力と月次 / 年次集計
- optional OIDC認証、SQLite / PostgreSQL対応

## Quick start

reference development environmentはVS Code Dev Containerです。containerを開いた状態で:

```bash
cp .env.sample .env
```

sampleはlocal開発用の `SERVICE_PORT=8000` を含むため、そのまま起動できます。
`VERSION` は `docker-build` / `docker-run` / `closed-bundle` 等のversioned image/package targetを使う場合だけ設定します。

起動:

```bash
make install
make run
```

http://localhost:8000 を開きます。

セットアップ、architecture、認証、API、deployment等の詳細は **[Documentation](docs/README.md)** を参照してください。
