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

## 6. 作業ステップ (各管理機能ごと)

以下に、**社員管理 (`user`)** を例として、具体的な作業ステップを詳細に記述します。他の管理機能 (`group`, `user_type`, `location`) についても、エンティティ名 (`user`) を適宜読み替えながら、同様の手順を適用します。

**ステップ 0: スキーマへの `as_form` 実装**

   - [ ] HTMX フォームからのデータ受け取りに使用する Pydantic スキーマに `as_form` クラスメソッドを実装します。これは、リファクタリング対象の各管理機能 (`user`, `group`, `user_type`, `location`) の `Create` スキーマと `Update` スキーマに対して行います。
       - `app/schemas/user.py`: `UserCreate`, `UserUpdate`
       - `app/schemas/group.py`: `GroupCreate`, `GroupUpdate`
       - `app/schemas/user_type.py`: `UserTypeCreate`, `UserTypeUpdate`
       - `app/schemas/location.py`: `LocationCreate`, `LocationUpdate`
       - *参考: `as_form` の実装は、FastAPI のドキュメントやコミュニティの例を参照してください。通常、`@classmethod` デコレータと `Form(...)` を使用して実装されます。*

**ステップ 1: サービス層の作成とビジネスロジックの移行**

   - [ ] **`app/services/` ディレクトリを新規作成**します (まだ存在しない場合)。
   - [ ] **`app/services/user_service.py` を新規作成**します。
   - [ ] `app/routers/api/v1/user.py` および `app/routers/pages/user.py` (もし存在すれば) から、ユーザー作成・更新時に関連するビジネスロジック（例: グループ ID、社員種別 ID の存在チェック、ユーザー ID やユーザー名の重複チェックなど）を `user_service.py` にサービス関数として切り出します。
       - 例: `async def validate_user_dependencies(db: Session, group_id: int, user_type_id: int)`
       - 例: `async def validate_user_creation(db: Session, user_in: schemas.UserCreate)`
       - 例: `async def validate_user_update(db: Session, user_id: str, user_in: schemas.UserUpdate)`
   - [ ] バリデーションと CRUD 操作を組み合わせたサービス関数を `user_service.py` に作成します。
       - 例: `async def create_user_with_validation(db: Session, user_in: schemas.UserCreate) -> models.User:`
       - 例: `async def update_user_with_validation(db: Session, user_id: str, user_in: schemas.UserUpdate) -> models.User:`
   - [ ] `app/routers/api/v1/user.py` の `create_user` および `update_user` エンドポイントを修正し、切り出したビジネスロジックの代わりに、上記で作成したサービス関数を呼び出すように変更します。

**ステップ 2: CRUD 層の修正 (必要に応じて)**

   - [ ] HTML フラグメント (`_user_row.html`) のレンダリングに必要な関連情報（グループ名、社員種別名）を含めてユーザー情報を取得する関数を `app/crud/user.py` に**追加**します。
       - 例: `def get_user_with_details(db: Session, user_id: str) -> Optional[models.User]:`

**ステップ 3: 部分テンプレートの作成 (`app/templates/components/user/`)**

   - [ ] **`app/templates/components/user/` ディレクトリを新規作成**します (まだ存在しない場合)。
   - [ ] **`app/templates/components/user/_user_row.html` を新規作成**します。
   - [ ] **`app/templates/components/user/_user_edit_form.html` を新規作成**します。
   - [ ] **`app/templates/components/common/_form_error.html` を新規作成**します (まだ存在しない場合)。

**ステップ 4: バックエンド API の追加・修正 (`app/routers/pages/user.py`)**

   - [ ] **`app/routers/pages/user.py`** (なければ新規作成) に、HTMX から利用される以下のエンドポイントを追加します。
       - **`get_user_edit_form` (GET `/pages/user/edit/{user_id}`)**: 編集フォーム (`_user_edit_form.html`) をレンダリングして返す。
       - **`handle_create_user_row` (POST `/pages/user/row`)**: 新規ユーザーを作成し、新しいテーブル行 (`_user_row.html`) を返す。
       - **`handle_update_user_row` (PUT `/pages/user/row/{user_id}`)**: 既存ユーザーを更新し、更新されたテーブル行 (`_user_row.html`) を返す。

**ステップ 5: フロントエンド テンプレートの修正 (`app/templates/pages/user/index.html`)**

   - [ ] ユーザー一覧テーブルの `<tbody>` タグに `id="user-table-body"` を追加します。
   - [ ] テーブルのループ処理を修正し、`_user_row.html` を `include` するように変更します。
   - [ ] **編集モーダル**のコンテナ (`<dialog id="edit-user-modal-{{ user.id }}">` と `<div id="modal-content-edit-user-{{ user.id }}">`) が適切に配置されていることを確認します。
   - [ ] **追加モーダル**内のフォーム (`<form id="add-user-form">`) に HTMX 属性を追加し、エラー表示領域、インジケータ、成功時のクローズ処理を実装します。

**ステップ 6: テストの実装と実行**

   - [ ] **サービス層テスト:** `app/tests/services/` (なければ作成) に `test_user_service.py` を作成し、ステップ 1 で作成したサービス関数の単体テストを実装・実行します (バリデーションロジック、正常系、異常系)。
   - [ ] **API テスト:** `app/tests/routers/pages/` (なければ作成) に `test_user_page.py` を作成し、ステップ 4 で追加・修正した以下のエンドポイントに対するテストを実装・実行します。
       - `get_user_edit_form` (GET): 正常時のステータスコード 200 と HTML 内容の部分検証、存在しない ID の場合の 404。
       - `handle_create_user_row` (POST): 正常時のステータスコード 200 と返却される `_user_row.html` の内容検証。バリデーションエラー時のステータスコード 4xx と `_form_error.html` の内容検証。
       - `handle_update_user_row` (PUT): 正常時のステータスコード 200 と返却される `_user_row.html` の内容検証。バリデーションエラー時のステータスコード 4xx と `_form_error.html` の内容検証。存在しない ID の場合の 404。
   - [ ] **既存 API テスト:** `app/tests/routers/api/v1/` (なければ作成) に `test_user_api.py` を作成し、`create_user`, `update_user` (サービス層呼び出しに変更後も JSON を返すこと)、`delete_user` (204 を返すこと) のテストを実装・実行します。

**ステップ 7: JavaScript のクリーンアップ**

   - [ ] 上記ステップが完了し、手動テストでも社員管理 (`user`) 機能が HTMX で完全に動作することを確認した後、`app/static/js/modal-handlers.js` から**ユーザー管理に関連する処理**を削除します。

## 7. 実施順序

以下の順序で、**各機能の実装とそのテストをセットで完了させながら**、段階的にリファクタリングを進めます。

1.  **スキーマ修正:** まずステップ 0 を実施し、リファクタリング対象**全機能**の関連スキーマに `as_form` を実装します。
2.  **サービス層準備:** `app/services/` ディレクトリと、対象**全機能**に対応する空のサービスファイル (`user_service.py`, `group_service.py` など) および `__init__.py` を作成します。
3.  **社員管理 (`user`)**: ステップ 1 から 7 を実施し、**実装とテストを完了**させます。
4.  **グループ管理 (`group`)**: 同様にステップ 1 から 7 (エンティティ名を読み替え) を実施し、**実装とテストを完了**させます。
5.  **社員種別管理 (`user_type`)**: 同様にステップ 1 から 7 を実施し、**実装とテストを完了**させます。
6.  **勤務場所管理 (`location`)**: 同様にステップ 1 から 7 を実施し、**実装とテストを完了**させます。
7.  **最終クリーンアップ:** 全ての管理機能のリファクタリングとテストが完了したら、不要になった JavaScript ファイル **`app/static/js/modal-handlers.js`** を削除し、テンプレートからの読み込みも削除します。（`apiClient.js` は他の機能で使用されているため削除しません）。最終的に `pytest` を実行し、全てのテストがパスすることを確認します。

## 8. 考慮事項

- **エラーハンドリング:** バックエンドはエラー時に `_form_error.html` を適切なステータスコードで返し、フロントエンドはそれを表示できるように `hx-target` や `HX-Retarget` を設定します。
- **ローディングインジケータ:** `hx-indicator` を適切に設定します。
- **URL生成:** `url_for()` を使用します。
- **Alpine.js との連携:** モーダル表示は `onclick`, 非表示は `htmx:afterRequest` などで連携します。
- **フォームデータの受け取り:** 各スキーマに実装された `as_form` を利用し、`Depends(schemas.<SchemaName>.as_form)` で受け取ります。
- **テスト:**
    - **テストディレクトリ構造:** `app/tests/` 下に `services/`, `routers/api/v1/`, `routers/pages/` といった形でテストファイルを配置します (例: `app/tests/routers/pages/test_user_page.py`)。
    - **テストカバレッジ:** リファクタリングと同時にテストを追加することで、コードカバレッジの向上を目指します。
    - **テストの実行:** 各機能の実装完了時に `pytest` を実行し、追加・修正したテストがパスすることを確認します。

</rewritten_file> 