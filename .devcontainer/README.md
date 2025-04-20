# DevContainer 開発環境

このディレクトリには、VSCode DevContainer を使用した開発環境の設定が含まれています。

## 特記事項

### フロントエンドライブラリについて

DevContainer 環境では、アプリケーションの起動時に以下のフロントエンドライブラリを自動的に取得します：

- htmx.min.js
- alpine.min.js

これらのファイルは、コンテナ内の `/app/app/static/js/` ディレクトリに保存され、ホストマシンのファイルシステムへのマウン
トによって上書きされないように設定されています。

## 開発環境の起動方法

1. VSCode と Docker をインストールします
2. VSCode の拡張機能
   [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) をイン
   ストールします
3. プロジェクトを VSCode で開き、コマンドパレット（F1）から `Remote-Containers: Reopen in Container` を実行します
