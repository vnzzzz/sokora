# Sokora プロジェクト - 開発環境セットアップ

## VSCode Devcontainer を使用した開発環境

このプロジェクトは VSCode Devcontainer を利用して簡単に開発環境を構築できます。

### 前提条件

- [Visual Studio Code](https://code.visualstudio.com/) がインストールされていること
- [Docker](https://www.docker.com/) がインストールされていること
- VSCode の拡張機能
  [Remote - Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) がインス
  トールされていること

### 開発環境の起動方法

1. VSCode で Sokora プロジェクトのフォルダを開きます
2. コマンドパレット（`Ctrl+Shift+P` または `Cmd+Shift+P`）を開き、`Remote-Containers: Reopen in Container`を選択します
3. VSCode が Devcontainer を構築し、コンテナ内でプロジェクトを開きます

### 開発環境の特徴

- Python 3.13 環境が自動的に構築されます
- 必要なライブラリは自動的にインストールされます
- コードフォーマッタ（Black）や静的解析ツール（MyPy）が設定済みです
- 開発サーバーはホットリロードに対応しています
- プロジェクトのコードはローカルとコンテナで同期されます

### 開発サーバーの起動

コンテナ内のターミナルで以下のコマンドを実行します：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

コンテナ起動時に自動的に開発サーバーが起動します。`http://localhost:8000`にアクセスすることでアプリケーションを確認でき
ます。

### 環境変数の設定

デフォルトでは`.env`ファイルの環境変数が読み込まれます。開発環境専用の環境変数を設定したい場合は、`.env.development`ファ
イルを作成してください。
