# 管理機能における編集・削除処理の HTMX 化リファクタリング計画

## 1. 背景と目的

現在、Sokora アプリケーションの社員管理、グループ管理、社員種別管理、勤務場所管理といった主要な管理機能において、項目の追加・編集・削除処理は、主に `app/static/js/modal-handlers.js` 内の JavaScript 関数によって実装されています。特に、編集操作後の UI 更新 (`updateUIAfterEdit` 関数による DOM 操作) や、削除操作後のテーブル行の削除は、クライアントサイドの JavaScript に大きく依存しています。この実装方式は、管理対象のエンティティが増えるたびに `modal-handlers.js` の修正が必要となり、コードの複雑化と保守性の低下を招いています。

本リファクタリングの目的は、これらの管理機能におけるデータ操作処理を HTMX を活用して改善することです。具体的には、**既存の JSON 形式の API エンドポイント (`/api/v1/*`) は外部システム連携などの可能性を考慮して維持**しつつ、HTMX からのリクエストに応じて HTML フラグメント（例: テーブルの行 `<tr>`）を返す**新しい専用エンドポイント (`/pages/<entity>/row` など) を各管理機能のページルーター (`app/routers/pages/*.py`) に追加・修正**します。フロントエンドは、これらの新しいエンドポイントや適切に修正された既存エンドポイントに対して HTMX 属性 (`hx-get`, `hx-post`, `hx-put`, `hx-delete` など) を用いてリクエストを送信し、サーバーから返却された HTML フラグメントで UI の部分更新を行います。

これにより、API の汎用性を損なうことなく、JavaScript による複雑な DOM 操作を大幅に削減し、フロントエンドとバックエンドのコードをシンプル化、テスト容易性を向上させ、全体的な保守性を高めることを目指します。

## 2. 前提条件

リファクタリングをスムーズに進めるために、以下の前提条件が満たされていることを確認します。

- **Jinja2 テンプレートエンジンの設定:** FastAPI アプリケーション全体で Jinja2 が利用可能であること。具体的には、`app/main.py` や共通の依存性解決モジュール (`app/db/deps.py` など) で `templates = Jinja2Templates(directory="app/templates")` のようにインスタンスが生成され、各ルーターで `Request` オブジェクトと共に依存性注入 (`Depends(deps.get_templates)`) されていること。これにより、API ルーター内で `TemplateResponse` を使用して HTML フラグメントをレンダリングできます。
- **FastAPI の依存性注入:** 各 API エンドポイントにおいて、データベースセッション (`db: Session = Depends(deps.get_db)`) やリクエストオブジェクト (`request: Request`) が FastAPI の依存性注入システムを通じて適切に利用可能であること。
- **Pydantic スキーマの `as_form` 実装:** HTMX フォームからのデータを受け取るために、関連する Pydantic スキーマ (例: `schemas.UserCreate`, `schemas.UserUpdate`) に `as_form` クラスメソッドが**実装されている、または本リファクタリングの一環として実装される**こと。

## 3. 現状分析

リファクタリング計画を具体化するために、現在の実装状況を詳細に分析します。

- **フロントエンド (`app/templates/` および `app/static/js/`):**
    - `app/static/js/modal-handlers.js`: 各管理ページ (`app/templates/pages/*/index.html`) から `setupAddFormHandler`, `setupEditFormHandlers`, `setupDeleteHandlers` といった関数が呼び出されています。これらの関数は、`app/static/js/apiClient.js` を介してバックエンドの JSON API (`/api/v1/*`) を呼び出し、レスポンスに基づいて一部の DOM 更新（編集時の値書き換え、削除時の行削除）を行っています。
    - `updateUIAfterEdit` 関数: 編集成功時に、JavaScript を用いて対応するテーブル行 (`<tr>`) の内容を直接書き換えています。
    - `setupDeleteHandlers` 関数: 削除成功時に、JavaScript を用いて対応するテーブル行 (`<tr>`) を DOM から削除しています。
    - 各管理ページテンプレート (`app/templates/pages/*/index.html`): テーブル行 (`<tr>`) には `id` 属性 (例: `id="user-row-{{ user.id }}"`) が付与されています。編集ボタンや削除ボタンには、操作対象の ID を示す `data-*` 属性が付与されている場合があります。追加フォームおよび編集フォームの送信処理は、現在 JavaScript によって制御されています。
    - 編集モーダル: 一部の管理機能では、編集ボタンクリック時に `hx-get` を使用してモーダルのコンテンツ（フォーム部分）を非同期に読み込んでいる可能性がありますが、フォーム送信自体は JavaScript 制御です。
- **バックエンド (`app/routers/`, `app/crud/`, `app/services/`):**
    - **CRUD API エンドポイント (`app/routers/api/v1/*.py`):**
        - **POST (作成):** 成功時に作成されたリソース（例: ユーザー情報）を JSON 形式で返します。
        - **PUT (更新):** 成功時に更新されたリソースを JSON 形式で返します。
        - **DELETE (削除):** 関連する全ての管理機能 (`user`, `group`, `user_type`, `location`) において、**成功時に `Response(status_code=status.HTTP_204_NO_CONTENT)` を返す実装に既に統一されています。**
    - **CRUD 操作 (`app/crud/*.py`):** データベースへのアクセスロジックは、各エンティティに対応する `app/crud/<entity>.py` モジュール内の関数で実装されています。これらの多くは、共通の基盤クラス `CRUDBase` (`app/crud/base.py`) を継承・利用しています。
    - **HTML ページ提供エンドポイント (`app/routers/pages/*.py`):** 各管理機能のメインページ (一覧表示など) を提供するエンドポイントがこれらのファイル内に存在します。
    - **サービス層 (`app/services/`):** **現状、`app/services/` ディレクトリおよびサービス層に該当するファイルは存在しません。**
    - **ビジネスロジック:** データのバリデーション（例: 重複チェック、依存関係チェック）や、より複雑な業務ルールなどのビジネスロジックは、主に API ルーター (`app/routers/api/v1/*.py` や `app/routers/pages/*.py`) 内に直接記述されています。
- **テスト (`app/tests/`):**
    - `app/tests/conftest.py` が存在し、`pytest` を利用したテスト基盤が用意されています。特に、**非同期テストクライアント (`httpx.AsyncClient`) を提供する `async_client` フィクスチャ**が定義されており、API テストの実装が可能です。
    - **現状、ルーターレベルでのテスト (`app/tests/routers/`) は存在しないか、限定的である可能性が高いです。**

## 4. リファクタリング方針

**基本戦略:** 外部システム連携や将来的な利用も考慮し、既存の JSON API (`/api/v1/*`, 実装: `app/routers/api/v1/*.py`) は原則として**現状のインターフェースを維持**します。これとは別に、**Web UI (HTMX) からの部分更新専用**として、HTML フラグメント (`<tr>` など) を返す API エンドポイント (`/pages/<entity>/row` など) をページルーター (`app/routers/pages/*.py`) に**追加・修正**します。

**コアロジックの共通化と責務分離を徹底**し、コードの重複を排除し保守性を向上させるため、以下の原則に従います。

- **API エンドポイント戦略:**
    - **JSON API (`/api/v1/<entity>`)**: 主に**データ操作と外部システム連携**を目的とし、原則として JSON 形式でリクエストを受け付け、JSON 形式でレスポンスを返します。実装は `app/routers/api/v1/<entity>.py` に配置します。既存の仕様を維持します。
    - **HTML フラグメント API (`/pages/<entity>/row` 等)**: 主に **Web UI (HTMX) からの部分更新**を目的とし、`Depends(schemas.<SchemaName>.as_form)` を使用してフォームデータを受け付け、HTML フラグメント (`<tr>` など) を `HTMLResponse` で返します。実装は `app/routers/pages/<entity>.py` に**追加**します。
    - **DELETE API (`/api/v1/<entity>/{id}`)**: 削除操作は比較的シンプルであり、既に `/api/v1/*` (実装: `app/routers/api/v1/<entity>.py`) で `Response(status_code=204)` を返すように統一されているため、これを HTMX からもそのまま利用します (HTMX は空レスポンスを受け取ると `hx-target` で指定された要素を削除します)。
    - **コアロジック共通化 (最重要):**
        - **CRUD操作:** データベースへの基本的な読み書き (Create, Read, Update, Delete) は、**`app/crud/*.py` 内の関数 (`CRUDBase` を利用)** に完全に集約します。JSON API (`app/routers/api/v1/*.py`) と HTML API (`app/routers/pages/*.py`) の両方が、**必ず同じ CRUD 関数を呼び出す**ように実装します。例えば、`crud.user.create`, `crud.user.update`, `crud.user.remove` などです。
        - **データ取得:** API がレスポンス生成（JSON または HTML）に必要なデータを取得するロジックも共通化します。特に HTML フラグメント生成に必要な関連データ（例: ユーザーに紐づくグループ名、社員種別名）を効率的に取得するため、**`app/crud/<entity>.py` に専用の取得関数 (`get_<entity>_with_details` など) を必要に応じて追加**するか、後述する**新規作成する `app/services/<entity>_service.py` でデータ取得ロジックを実装**します。
        - **ビジネスロジック/バリデーション/権限チェック:** 単純な CRUD 操作を超えるロジック（例: データの整合性チェック、依存関係の検証、複雑な業務ルール、権限チェックなど）は、**新規作成する `app/services/` ディレクトリ** とその配下の **`app/services/<entity>_service.py`** に切り出します。既存の API ルーター (`app/routers/api/v1/*.py` および `app/routers/pages/*.py`) 内に存在するこれらのロジックは、この新しいサービス層の関数呼び出しに置き換えます。これにより、ビジネスロジックの重複を排除し、テスト容易性を向上させます。
            - 例: `app/routers/api/v1/user.py` 内にあるグループや社員種別の存在チェックロジックは、**新規作成する `app/services/user_service.py`** に `validate_user_dependencies` や、バリデーションを含む作成/更新関数 `create_user_with_validation`, `update_user_with_validation` として実装し、ルーターからはこれらのサービス関数を呼び出すように変更します。
- **部分テンプレートの活用:**
    - UI の構成要素を再利用可能にするため、Jinja2 の部分テンプレートを活用します。
    - テーブル行 (`<tr>`) を表示するための部分テンプレートは、**新規作成する `app/templates/components/<entity>/`** ディレクトリ (例: `app/templates/components/user/`) 内に `_<entity>_row.html` (例: `_user_row.html`) として配置します。コンテキスト変数 (例: `user`) を受け取り、そのデータに基づいて行をレンダリングします。
    - 編集フォームを表示するための部分テンプレートも同様に、`app/templates/components/<entity>/_<entity>_edit_form.html` (例: `_user_edit_form.html`) として配置します。編集対象のデータ (例: `user`) や関連データ (例: 全グループリスト) をコンテキスト変数として受け取ります。
    - フォーム送信時のバリデーションエラーなどを統一的に表示するため、共通のエラー表示用テンプレートを **新規作成する `app/templates/components/common/_form_error.html`** として用意し、各 API エンドポイントから利用します。

## 5. 対象となる管理機能

本リファクタリング計画の対象となる管理機能は以下の通りです。

- [ ] 社員管理 (`user`)
- [ ] グループ管理 (`group`)
- [ ] 社員種別管理 (`user_type`)
- [ ] 勤務場所管理 (`location`)

## 6. 共通準備ステップ

以下のステップは、すべての管理機能に共通する準備作業です。

**ステップ 0: スキーマへの `as_form` 実装 (実施済み)**

   - [x] HTMX フォームからのデータ受け取りに使用する Pydantic スキーマに `as_form` クラスメソッドを実装します。これは、リファクタリング対象の各管理機能 (`user`, `group`, `user_type`, `location`) の `Create` スキーマと `Update` スキーマに対して行います。
       - [x] `app/schemas/user.py`: `UserCreate`, `UserUpdate`
       - [x] `app/schemas/group.py`: `GroupCreate`, `GroupUpdate`
       - [x] `app/schemas/user_type.py`: `UserTypeCreate`, `UserTypeUpdate`
       - [x] `app/schemas/location.py`: `LocationCreate`, `LocationUpdate`
       - *参考: `as_form` の実装は、FastAPI のドキュメントやコミュニティの例を参照してください。通常、`@classmethod` デコレータと `Form(...)` を使用して実装されます。*

**ステップ 1: サービス層の準備**

   - [x] **`app/services/` ディレクトリを新規作成**します (まだ存在しない場合)。
   - [x] `app/services/` 内に、対象となる各管理機能に対応する空のサービスファイル (`user_service.py`, `group_service.py`, `user_type_service.py`, `location_service.py`) と、ディレクトリを Python パッケージとして認識させるための `__init__.py` を作成します。
   - [x] 同様に、テスト用のディレクトリ **`app/tests/services/` を新規作成**し、空の `__init__.py` を作成します。

**ステップ 2: 部分テンプレートの準備**

   - [x] **`app/templates/components/common/_form_error.html` を新規作成**し、フォームエラーを共通的に表示するテンプレートを用意します (まだ存在しない場合)。
   - [x] 対象となる各管理機能に対応する部分テンプレート用ディレクトリ **`app/templates/components/<entity>/`** (例: `user/`, `group/` など) を新規作成します。
   - [x] 同様に、テスト用のディレクトリ **`app/tests/routers/pages/`** と **`app/tests/routers/api/v1/`** を新規作成し、それぞれに空の `__init__.py` を作成します (まだ存在しない場合)。

## 7. 管理機能別リファクタリング

以下のセクションで、各管理機能 (`user`, `group`, `user_type`, `location`) のリファクタリング手順と進捗を個別に管理します。実施順序に従い、各機能のステップ3から9までを順に完了させてください。

**各ステップの進め方:**
1.  **現状確認:** そのステップに関連する既存のコード（ルーター、CRUD、サービス、テンプレート等）を確認します。
2.  **計画詳細化:** 確認した内容に基づき、そのステップでの具体的な作業内容（作成・修正するファイル、関数、ロジック等）を詳細化します。
3.  **実行:** 計画に従ってコードの編集やファイルの作成を行います。
4.  **テスト:** 計画で定義されたタイミングで自動テストを実行し、変更による影響を確認・修正します。

### 7.1 社員管理 (user)

**ステップ 3: ビジネスロジックのサービス層への移行**

   - [x] `app/routers/api/v1/user.py` および `app/routers/pages/user.py` から、ユーザー作成・更新時に関連するビジネスロジック（例: グループ ID、社員種別 ID の存在チェック、ユーザー ID やユーザー名の重複チェックなど）を `app/services/user_service.py` にサービス関数として切り出しました。
       - 例: `validate_dependencies`, `validate_user_creation`, `validate_user_update`
   - [x] バリデーションと CRUD 操作を組み合わせたサービス関数を `app/services/user_service.py` に作成しました。
       - 例: `create_user_with_validation`, `update_user_with_validation`
   - [x] `app/routers/api/v1/user.py` の `create_user` および `update_user` エンドポイントを修正し、切り出したビジネスロジックの代わりに、上記で作成したサービス関数を呼び出すように変更しました。
   - [x] **テスト実行(1):** 関連する既存APIテスト (`tests/routers/api/v1/test_user.py`) を実行し、意図しない挙動破壊がないか確認、必要に応じて修正しました。

**ステップ 4: CRUD 層の修正 (必要に応じて)**

   - [x] HTML フラグメント (`_user_row.html`) のレンダリングに必要な関連情報（グループ名、社員種別名）を含めてユーザー情報を取得する関数 `get_user_with_details` を `app/crud/user.py` に**追加**しました。

**ステップ 5: 部分テンプレートの作成 (`app/templates/components/user/`)**

   - [x] **`app/templates/components/user/_user_row.html` を新規作成**し、テーブル行のHTMLを定義しました。
   - [x] **`app/templates/components/user/_user_edit_form.html` を新規作成**し、編集フォームのHTMLを定義しました。

**ステップ 6: バックエンド API の追加・修正 (`app/routers/pages/user.py`)**

   - [x] **`app/routers/pages/user.py`** に、HTMX から利用される以下のエンドポイントを追加しました。
       - **`get_user_edit_form` (GET `/pages/user/edit/{user_id}`)**: 編集フォーム (`_user_edit_form.html`) をレンダリングして返す。
       - **`handle_create_user_row` (POST `/pages/user/row`)**: 新規ユーザーを作成し、新しいテーブル行 (`_user_row.html`) を返す。サービス層関数 (`create_user_with_validation`) を呼び出す。
       - **`handle_update_user_row` (PUT `/pages/user/row/{user_id}`)**: 既存ユーザーを更新し、更新されたテーブル行 (`_user_row.html`) を返す。サービス層関数 (`update_user_with_validation`) を呼び出す。
   - [x] **テスト実装・実行(2):** このステップで追加・修正したページAPIエンドポイントのテスト (`tests/routers/pages/test_user_page.py`) を実装し、実行しました。

**ステップ 7: フロントエンド テンプレートの修正 (`app/templates/pages/user/index.html`)**

   - [x] テーブルの各行 (`<tr>`) を生成するループ処理を修正し、ステップ 5 で作成した `_user_row.html` を `include` するように変更しました。各行の `<tr>` タグには `id="user-row-{{ user.id }}"` を付与しています。
   - [x] **編集ボタン**: `hx-get="/pages/user/edit/{{ user.id }}"`、`hx-target="#modal-content-edit-user-{{ user.id }}"` などの属性を追加し、クリック時に編集フォームをモーダル内にロードするようにしました。
   - [x] **編集モーダル**: 編集フォームをロードするコンテナ (`<div id="modal-content-edit-user-{{ user.id }}">`) を用意し、モーダル内のフォーム (`<form>`) に `hx-put="/pages/user/row/{{ user.id }}"` などの属性を追加しました。（成功時はページリロードのため `hx-target` は不要）
   - [x] **追加モーダル**: フォーム (`<form id="add-user-form">`) に `hx-post="/pages/user/row"` 属性が追加されています。成功時はバックエンドからの `HX-Trigger` によるページリロードでテーブルが更新され、エラー時は `HX-Retarget` でエラー表示領域が更新されるため、フォーム自体への `hx-target`/`hx-swap` 属性は不要であり、設定されていません。
   - [x] **削除ボタン**: 削除確認モーダル内の確定ボタンに `hx-delete="/api/v1/user/{{ user.id }}"`、`hx-target="closest tr"`、`hx-swap="outerHTML swap:1s"`、`hx-confirm` が設定されています (削除は既存 API を利用)。
   - [x] エラー表示領域 (`_form_error.html` を include)、ローディングインジケータ (`loading_indicator`)、モーダルを閉じる処理 (`HX-Trigger` でのリロードまたは Alpine.js) が実装されています。
   - [x] **テスト実行(3):** 関連する自動テスト（サービス層、ページAPI、既存API）はパスしています。手動での動作確認は未実施です。

**ステップ 8: テストの最終確認と実装**

   - [x] これまでのステップで追加・修正したテストがすべて実装され、パスすることを確認しました。
       - [x] サービス層テスト (`test_user_service.py`)
       - [x] ページ API テスト (`test_user_page.py`)
       - [x] 既存 API テスト (`test_user.py` - ステップ3で確認・修正済み)

**ステップ 9: JavaScript のクリーンアップ (`user` 関連部分)**

   - [x] `modal-handlers.js` の `updateUIAfterEdit` 関数から、不要になったユーザー関連のコードブロックを削除しました。他の汎用関数 (`setup...`) は、他エンティティでまだ使用されている可能性があるため残しています。
   - [x] **テスト実行(4):** 関連する自動テストはすべてパスしています。

### 7.2 グループ管理 (group)

**ステップ 3: ビジネスロジックのサービス層への移行**

   - [x] `app/routers/api/v1/group.py` および `app/routers/pages/group.py` (もし存在すれば) から、グループ作成・更新時に関連するビジネスロジック（例: グループ名の重複チェックなど）を `app/services/group_service.py` にサービス関数として切り出しました。
       - 例: `validate_group_creation`, `validate_group_update`
   - [x] バリデーションと CRUD 操作を組み合わせたサービス関数を `app/services/group_service.py` に作成しました。
       - 例: `create_group_with_validation`, `update_group_with_validation`
   - [x] `app/routers/api/v1/group.py` の `create_group` および `update_group` エンドポイントを修正し、切り出したビジネスロジックの代わりに、上記で作成したサービス関数を呼び出すように変更しました。
   - [x] **テスト実行(1):** 関連する既存APIテスト (`tests/routers/api/v1/test_group_api.py`) を実行し、意図しない挙動破壊がないことを確認しました。
   - [x] **テスト実装(1):** サービス層のテスト (`tests/services/test_group_service.py`) を実装し、実行しました。

**ステップ 4: CRUD 層の修正 (必要に応じて)**

   - [x] (グループ管理では通常不要。関連情報が少ないため)

**ステップ 5: 部分テンプレートの作成 (`app/templates/components/group/`)**

   - [x] **`app/templates/components/group/_group_row.html` を新規作成**します。
   - [x] **`app/templates/components/group/_group_edit_form.html` を新規作成**します。

**ステップ 6: バックエンド API の追加・修正 (`app/routers/pages/group.py`)**

   - [x] **`app/routers/pages/group.py`** (なければ新規作成) に、HTMX から利用される以下のエンドポイントを追加します。
       - **`get_group_edit_form` (GET `/pages/group/edit/{group_id}`)**: 編集フォーム (`_group_edit_form.html`) をレンダリングして返す。
       - **`handle_create_group_row` (POST `/pages/group/row`)**: 新規グループを作成し、新しいテーブル行 (`_group_row.html`) を返す。サービス層関数 (`create_group_with_validation`) を呼び出す。
       - **`handle_update_group_row` (PUT `/pages/group/row/{group_id}`)**: 既存グループを更新し、更新されたテーブル行 (`_group_row.html`) を返す。サービス層関数 (`update_group_with_validation`) を呼び出す。
   - [x] **テスト実装・実行(2):** ページAPIエンドポイントのテスト (`tests/routers/pages/test_group_page.py`) を実装し、実行します。

**ステップ 7: フロントエンド テンプレートの修正 (`app/templates/pages/group/index.html`)**

   - [x] テーブルやボタン、モーダルにHTMX属性を追加・修正します。
   - [x] **テスト実行(3):** 自動テスト再実行。手動確認推奨。

**ステップ 8: テストの最終確認と実装**

   - [x] これまでのステップで追加・修正したテストがすべて実装され、パスすることを確認しました。
       - [x] サービス層テスト (`test_group_service.py`)
       - [x] ページ API テスト (`test_group_page.py`)
       - [x] 既存 API テスト (`test_group.py`)

**ステップ 9: JavaScript のクリーンアップ (`group` 関連部分)**

   - [x] `modal-handlers.js` の `updateUIAfterEdit` 関数から、不要になったグループ関連のコードブロックを削除しました。
   - [x] **テスト実行(4):** 関連する自動テストをすべて再実行し、パスすることを確認しました。

### 7.3 社員種別管理 (user_type)

**ステップ 3: ビジネスロジックのサービス層への移行**

   - [ ] `app/routers/api/v1/user_type.py` および `app/routers/pages/user_type.py` (もし存在すれば) から、社員種別作成・更新時に関連するビジネスロジック（例: 社員種別名の重複チェックなど）を `app/services/user_type_service.py` にサービス関数として切り出します。
       - 例: `validate_user_type_creation`, `validate_user_type_update`
   - [ ] バリデーションと CRUD 操作を組み合わせたサービス関数を `app/services/user_type_service.py` に作成します。
       - 例: `create_user_type_with_validation`, `update_user_type_with_validation`
   - [ ] `app/routers/api/v1/user_type.py` の `create_user_type` および `update_user_type` エンドポイントを修正し、切り出したビジネスロジックの代わりに、上記で作成したサービス関数を呼び出すように変更します。
   - [ ] **テスト実行(1):** `test_user_type_api.py` を実行・修正。
   - [ ] **テスト実装(1):** `test_user_type_service.py` の実装開始。

**ステップ 4: CRUD 層の修正 (必要に応じて)**

   - [ ] (通常不要)

**ステップ 5: 部分テンプレートの作成 (`app/templates/components/user_type/`)**

   - [ ] **`app/templates/components/user_type/_user_type_row.html` を新規作成**します。
   - [ ] **`app/templates/components/user_type/_user_type_edit_form.html` を新規作成**します。

**ステップ 6: バックエンド API の追加・修正 (`app/routers/pages/user_type.py`)**

   - [ ] **`app/routers/pages/user_type.py`** (なければ新規作成) に、HTMX から利用される以下のエンドポイントを追加します。
       - **`get_user_type_edit_form` (GET `/pages/user_type/edit/{user_type_id}`)**: 編集フォーム (`_user_type_edit_form.html`) をレンダリングして返す。
       - **`handle_create_user_type_row` (POST `/pages/user_type/row`)**: 新規社員種別を作成し、新しいテーブル行 (`_user_type_row.html`) を返す。サービス層関数 (`create_user_type_with_validation`) を呼び出す。
       - **`handle_update_user_type_row` (PUT `/pages/user_type/row/{user_type_id}`)**: 既存社員種別を更新し、更新されたテーブル行 (`_user_type_row.html`) を返す。サービス層関数 (`update_user_type_with_validation`) を呼び出す。
   - [ ] **テスト実装・実行(2):** このステップで追加・修正したページAPIエンドポイントのテスト (`tests/routers/pages/test_user_type_page.py`) を実装し、実行します。

**ステップ 7: フロントエンド テンプレートの修正 (`app/templates/pages/user_type/index.html`)**

   - [ ] テーブルやボタン、モーダルにHTMX属性を追加・修正します。
   - [ ] **テスト実行(3):** 自動テスト再実行。手動確認推奨。

**ステップ 8: テストの最終確認と実装**

   - [ ] 全テストの実装・パスを確認。
       - [ ] `test_user_type_service.py`
       - [ ] `test_user_type_page.py`
       - [ ] `test_user_type_api.py`

**ステップ 9: JavaScript のクリーンアップ (`user_type` 関連部分)**

   - [ ] `modal-handlers.js` から関連処理を削除します。
   - [ ] **テスト実行(4):** 自動テスト再実行。

### 7.4 勤務場所管理 (location)

**ステップ 3: ビジネスロジックのサービス層への移行**

   - [ ] `app/routers/api/v1/location.py` および `app/routers/pages/location.py` (もし存在すれば) から、勤務場所作成・更新時に関連するビジネスロジック（例: 勤務場所名の重複チェックなど）を `app/services/location_service.py` にサービス関数として切り出します。
       - 例: `validate_location_creation`, `validate_location_update`
   - [ ] バリデーションと CRUD 操作を組み合わせたサービス関数を `app/services/location_service.py` に作成します。
       - 例: `create_location_with_validation`, `update_location_with_validation`
   - [ ] `app/routers/api/v1/location.py` の `create_location` および `update_location` エンドポイントを修正し、切り出したビジネスロジックの代わりに、上記で作成したサービス関数を呼び出すように変更します。
   - [ ] **テスト実行(1):** `test_location_api.py` を実行・修正。
   - [ ] **テスト実装(1):** `test_location_service.py` の実装開始。

**ステップ 4: CRUD 層の修正 (必要に応じて)**

   - [ ] (通常不要)

**ステップ 5: 部分テンプレートの作成 (`app/templates/components/location/`)**

   - [ ] **`app/templates/components/location/_location_row.html` を新規作成**します。
   - [ ] **`app/templates/components/location/_location_edit_form.html` を新規作成**します。

**ステップ 6: バックエンド API の追加・修正 (`app/routers/pages/location.py`)**

   - [ ] **`app/routers/pages/location.py`** (なければ新規作成) に、HTMX から利用される以下のエンドポイントを追加します。
       - **`get_location_edit_form` (GET `/pages/location/edit/{location_id}`)**: 編集フォーム (`_location_edit_form.html`) をレンダリングして返す。
       - **`handle_create_location_row` (POST `/pages/location/row`)**: 新規勤務場所を作成し、新しいテーブル行 (`_location_row.html`) を返す。サービス層関数 (`create_location_with_validation`) を呼び出す。
       - **`handle_update_location_row` (PUT `/pages/location/row/{location_id}`)**: 既存勤務場所を更新し、更新されたテーブル行 (`_location_row.html`) を返す。サービス層関数 (`update_location_with_validation`) を呼び出す。
   - [ ] **テスト実装・実行(2):** ページAPIエンドポイントのテスト (`tests/routers/pages/test_location_page.py`) を実装し、実行します。

**ステップ 7: フロントエンド テンプレートの修正 (`app/templates/pages/location/index.html`)**

   - [ ] テーブルやボタン、モーダルにHTMX属性を追加・修正します。
   - [ ] **テスト実行(3):** 自動テスト再実行。手動確認推奨。

**ステップ 8: テストの最終確認と実装**

   - [ ] 全テストの実装・パスを確認。
       - [ ] `test_location_service.py`
       - [ ] `test_location_page.py`
       - [ ] `test_location_api.py`

**ステップ 9: JavaScript のクリーンアップ (`location` 関連部分)**

   - [ ] `modal-handlers.js` から関連処理を削除します。
   - [ ] **テスト実行(4):** 自動テスト再実行。

## 8. 実施順序

以下の順序でリファクタリングを進めます。

1.  **共通準備:** ステップ 0, 1, 2 を実施済み。
2.  **管理機能別実施:** 次に、「7. 管理機能別リファクタリング」の各サブセクションを以下の順序で実施します。**各管理機能のステップ内では、実装とテストを適宜交互に行い、問題を早期に発見します。**
    1.  **7.1 社員管理 (`user`)** (ステップ3, 4 完了済み)
    2.  **7.2 グループ管理 (`group`)**
    3.  **7.3 社員種別管理 (`user_type`)**
    4.  **7.4 勤務場所管理 (`location`)**
3.  **最終クリーンアップ:** 全ての管理機能のリファクタリングとテストが完了したら、... (略)

## 9. 考慮事項

// ... existing code ...

## 10. テスト実行方法

リファクタリング中の各ステップで定義されたテストは、プロジェクトルートディレクトリから以下のスクリプトを実行することで実施できます。

```bash
./scripts/testing/run_test.sh
```

このスクリプトは `pytest` を使用して `app/tests/` ディレクトリ以下のすべてのテストを実行します。