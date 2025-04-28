# 管理機能における編集・削除処理の HTMX 化リファクタリング計画

## 1. 背景と目的

現在、社員管理、グループ管理などの管理機能における項目の追加・編集・削除処理は、`modal-handlers.js` 内の JavaScript 関数によって行われている。特に編集後のUI更新 (`updateUIAfterEdit`) や削除後の行削除は、JavaScript による DOM 操作に依存しており、管理対象が増えるごとに `modal-handlers.js` の修正が必要となり、保守性が低下している。

本リファクタリングでは、HTMX を活用してこれらの処理を改善する。**既存の JSON 形式の API エンドポイント (`/api/v1/*`) は外部連携等を考慮して維持**しつつ、HTMX からのリクエストに応じて HTML フラグメント（テーブル行など）を返す**新しい専用エンドポイント (`/pages/*/row` など) を作成**する。フロントエンドは、これらの新しいエンドポイントや適切に修正された既存エンドポイントに対して HTMX 属性 (`hx-*`) を使って部分更新を行う。これにより、API の汎用性を保ちながら JavaScript による DOM 操作を大幅に削減し、コードをシンプル化、保守性を向上させることを目的とする。

## 2. 前提条件

- **Jinja2 テンプレートエンジンの設定:** API ルーター (例: `app/routers/api/v1/*.py` や `app/routers/pages/*.py`) 内で `request: Request` を引数として受け取り、`TemplateResponse` を使用して HTML フラグメントをレンダリングできる状態であること。通常、`app/main.py` や共通の依存性注入で `templates = Jinja2Templates(directory="app/templates")` が設定されている。
- **FastAPI の依存性注入:** 各 API エンドポイントで `db: Session = Depends(deps.get_db)` や `request: Request` が適切に注入されていること。

## 3. 現状分析

- **フロントエンド:**
    - `modal-handlers.js`: `setupAddFormHandler`, `setupEditFormHandlers`, `setupDeleteHandlers` が各管理ページテンプレート (`app/templates/pages/*/index.html`) から呼び出され、`apiClient.js` を介して API をコールし、一部 DOM 更新を行う。
    - `updateUIAfterEdit`: 編集成功時に JavaScript でテーブル行の内容を更新。
    - `setupDeleteHandlers`: 削除成功時に JavaScript でテーブル行 (`<tr>`) を削除。
    - 各管理ページテンプレート: テーブル行 (`<tr>`) に `id` 属性 (例: `id="user-row-{{ user.id }}"`) が付与されている。編集/削除ボタンには `data-*` 属性 (例: `data-user-id`) が付与されている場合がある。追加・編集フォームの送信は JavaScript が制御。
    - 編集モーダルの内容は `hx-get` で非同期に読み込まれている場合がある。
- **バックエンド:**
    - CRUD API エンドポイント (`app/routers/api/v1/*.py`):
        - **POST:** 成功時に作成されたリソースを JSON で返す。
        - **PUT:** 成功時に更新されたリソースを JSON で返す。
        - **DELETE:** 成功時に JSON または 204 No Content を返す。
    - CRUD 操作は `app/crud/*.py` 内の関数で行われる。
    - HTML ページを提供するエンドポイントは `app/routers/pages/*.py` に存在する。
    - サービス層 (`app/services/*.py`) が作成された。

## 4. リファクタリング方針

**基本戦略として、外部システム連携用の JSON API (`/api/v1/*`, 実装は `app/routers/api/v1/*.py`) は維持し、UI 部分更新用の HTML フラグメント API (`/pages/*`, 実装は `app/routers/pages/*.py`) を追加・修正します。両者は明確に分離しつつ、データベース操作は `crud` 層、ビジネスロジックは `services` 層で実装し、コードの重複を避けます。**

- **API エンドポイント戦略:**
    - **JSON API (`/api/v1/<entity>`)**: **データ操作と外部システム連携** を主目的とし、原則として JSON 形式でレスポンスを返す。実装は `app/routers/api/v1/<entity>.py`。既存の仕様を維持する。
    - **HTML フラグメント API (`/pages/<entity>/row` 等)**: **Web UI (HTMX) からの部分更新** を目的とし、HTML フラグメント (`<tr>` 等) を `HTMLResponse` で返す。実装は `app/routers/pages/<entity>.py` に**追加**する。
    - **DELETE API (`/api/v1/<entity>/{id}`)**: 削除操作はシンプルであるため、既存の `/api/v1/*` (実装: `app/routers/api/v1/<entity>.py`) を流用し、成功時に `Response(status_code=204)` を返すように統一する (HTMX は空レスポンスで要素削除が可能)。
    - **コアロジック共通化**: HTML 返却用 API は、内部で既存の JSON API と同じ **`crud` 関数** や **`services` 関数** (バリデーション等) を呼び出し、コアロジックの重複を徹底的に避ける。
    - **コアロジック共通化の徹底 (重要):**
        - **CRUD操作:** データベースへの実際の読み書き (Create, Read, Update, Delete) は、`app/crud/*.py` 内の関数に集約する。JSONを返すAPIもHTMLを返すAPIも、**必ず同じCRUD関数を呼び出す**こと。既存の `crud` 関数が適切でない場合（例: 単純すぎる、副作用があるなど）は、この機会にリファクタリングする。
            - 例 (`crud.user.update_user`): 現在の実装は個別の引数を取り bool を返すため、`UserUpdate` スキーマを受け取り、更新後の `User` オブジェクト（リレーション含む）を返すように `CRUDBase.update` を利用またはオーバーライドする方向でリファクタリングが必要。（要確認）
        - **データ取得:** APIが必要とするデータ（リレーション含む）を取得するロジックも共通化する（通常は `crud` 内）。更新後や作成後にデータを再取得する際も共通の関数を利用する。
            - 例: HTMLフラグメント生成やJSONレスポンス生成に必要な関連データ（グループ名、社員種別名など）が効率的に取得できるように `crud` 層の `get` メソッドなどを調整する。
        - **ビジネスロジック/権限チェック:** 単純なCRUD以上のロジックや権限チェックは、**`app/services/*.py`** やヘルパー関数に切り出し、両方のエンドポイントタイプから呼び出す。既存実装でエンドポイント内にロジックが散在している場合は、積極的に共通化のためのリファクタリングを行う。
            - 例 (`app/routers/api/v1/user.py`): `create_user`, `update_user` 内のグループ・社員種別存在チェックは、**サービス関数 (`user_service.validate_user_creation` など)** に切り出すことを検討する。
- **部分テンプレートの活用:** 各管理対象（ユーザー、グループ等）のテーブル行 (`<tr>`) を表示するための部分テンプレート (`app/templates/components/<entity>/_row.html`) を新規作成し、HTML フラグメント API から利用する。
- **編集処理:**
    - **バックエンド (新規 PUT `/pages/<entity>/row/{id}`):** 成功時に、更新されたデータを使って新規作成した部分テンプレート (`_row.html`) をレンダリングし、その HTML フラグメントを `HTMLResponse(content=..., status_code=200)` で返す。
    - **フロントエンド (編集フォーム):** `hx-put` で新しい HTML 返却用エンドポイントを指定。`hx-target` (更新対象の行 ID), `hx-swap="outerHTML"` を付与。成功時にモーダルを閉じるイベントハンドラ (`hx-on::after-request`) を追加。JavaScript による送信処理と `data-*` 属性を削除。
- **削除処理:**
    - **バックエンド (既存 DELETE `/api/v1/<entity>/{id}`)**: 成功時に `Response(status_code=204)` を返すように修正。
    - **フロントエンド (削除ボタン):** `hx-delete` で既存の DELETE API エンドポイントを指定。`hx-target="closest tr"`, `hx-swap="outerHTML"` (空のレスポンスで要素が削除される), `hx-confirm` を付与。JavaScript による処理と `data-*` 属性を削除。
- **追加処理:**
    - **バックエンド (新規 POST `/pages/<entity>/row`):** 成功時に、作成されたデータを使って新規作成した部分テンプレート (`_row.html`) をレンダリングし、その HTML フラグメントを `HTMLResponse(content=..., status_code=200)` で返す。
    - **フロントエンド (追加フォーム):** `hx-post` で新しい HTML 返却用エンドポイントを指定。`hx-target` (テーブルの `<tbody>` ID), `hx-swap="beforeend"` を付与。成功時にフォームをリセットしモーダルを閉じるイベントハンドラ (`hx-on::after-request`) を追加。JavaScript による送信処理を削除。
- **JavaScript の段階的削除:**
    - 各管理機能の HTMX 化完了ごとに、`modal-handlers.js` 内の対応する処理（例: `user-row-` 関連の `updateUIAfterEdit` ロジック）を削除。
    - 全管理機能の HTMX 化完了後、`modal-handlers.js`, `apiClient.js` をプロジェクトから削除し、`app/templates/layout/head.html` などでの読み込み箇所も削除する。

## 5. 対象となる管理機能

- [ ] 社員管理 (`/user`)
- [ ] グループ管理 (`/groups`)
- [ ] 社員種別管理 (`/user_types`)
- [ ] 勤務場所管理 (`/locations`)

## 6. 作業ステップ (各管理機能ごと)

以下は **社員管理 (`/user`)** を例とした具体的な作業ステップ。他の管理機能 (`group`, `user_type`, `location`) も同様の手順で実施する。ファイルパスの `<entity>` 部分を適宜読み替える。

1.  **部分テンプレート作成 (`app/templates/components/user/_user_row.html`):**
    - [ ] 新規に `app/templates/components/user/` ディレクトリを作成する。
    - [ ] `app/templates/pages/user/index.html` 内のユーザーテーブルの `<tr>...</tr>` 部分をコピーして `app/templates/components/user/_user_row.html` を新規作成。`user` オブジェクトをコンテキスト変数として受け取る。
        ```html
        {# app/templates/components/user/_user_row.html #}
        <tr id="user-row-{{ user.id }}">
            {# 各セル (td) の内容 ... #}
            <td>{{ user.username }} ({{ user.user_id }})</td>
            <td>{{ user.user_type.name if user.user_type else '' }}</td>
            <td>{{ user.email }}</td>
            {# ... 他のセル ... #}
            <td>
                {# 編集ボタン: モーダル内容取得用 #}
                <button class="btn btn-sm btn-outline"
                        hx-get="{{ url_for('get_user_edit_form', user_id=user.id) }}"
                        hx-target="#modal-content-edit-user-{{ user.id }}"
                        hx-swap="innerHTML"
                        onclick="document.getElementById('edit-user-modal-{{ user.id }}').showModal()">
                    編集
                </button>
                {# 削除ボタン: HTMX化 #}
                <button class="btn btn-sm btn-error btn-outline"
                        hx-delete="{{ url_for('delete_user', user_id=user.id) }}"
                        hx-target="closest tr"
                        hx-swap="outerHTML"
                        hx-confirm="「{{ user.username }}」を削除してもよろしいですか？"
                        hx-indicator="#row-indicator-{{ user.id }}"> {# 行単位のインジケータ例 #}
                    削除
                </button>
                <span class="loading loading-spinner loading-xs htmx-indicator" id="row-indicator-{{ user.id }}"></span>
            </td>
        </tr>
        ```
    - [ ] `app/templates/pages/user/index.html` のテーブルループを修正し、`{% include "components/user/_user_row.html" with context %}` を使用するように変更。テーブルの `<tbody>` に `id="user-table-body"` を付与。

2.  **バックエンド API 修正:**
    - [ ] **コアロジックのリファクタリング (必要に応じて):**
        - [ ] `app/crud/user.py` の `update_user` を、`UserUpdate` スキーマを受け取り更新後の `User` を返すように修正する。
        - [ ] **新規** に `app/services/user_service.py` ファイルを作成し、`app/routers/api/v1/user.py` 内のグループ・社員種別存在チェックなどのビジネスロジックを共通のサービス関数に切り出す。
    - [ ] **既存 `app/routers/api/v1/user.py` の修正:**
        - **`delete_user` (DELETE `/api/v1/users/{user_id}`)**: 現在の実装で既に `Response(status_code=204)` を返しているため、**修正不要**。
        - `create_user` (POST), `update_user` (PUT): 内部のビジネスロジックを共通サービス関数呼び出しに置き換える。
    - [ ] **既存 `app/routers/pages/user.py` にエンドポイント追加:**
        - **コアロジック共通化の確認:** 以下の新規エンドポイントを実装する前に、関連する `crud.user` 関数や権限チェックロジックが適切に共通化・分離されているか確認し、必要であればリファクタリングを行う。
        - **`handle_create_user_row` (POST `/pages/user/row`)**: `request: Request`, `user_in: schemas.UserCreate = Depends(...)`, `db: Session` を引数に取り、内部で **共通化されたサービス関数/CRUD関数** (`user_service.create_user_with_validation` や `crud.user.create`) を呼び出す。成功後、作成/取得された `user` を取得し、`TemplateResponse` で **新規作成した `components/user/_user_row.html`** をレンダリングして `HTMLResponse` (status_code=200) で返す。
            - `Depends(schemas.UserCreate.as_form)` を使う場合は、`UserCreate` スキーマに `as_form` メソッドを実装する必要がある。
          ```python
          # 例: app/routers/pages/user.py (既存ファイルに追加)
          from fastapi import APIRouter, Depends, Request, status, HTTPException
          from fastapi.responses import HTMLResponse
          from fastapi.templating import Jinja2Templates
          from sqlalchemy.orm import Session
          from app.db import deps
          from app import crud, schemas
          from app.core.config import settings
          from app.core.logging_config import setup_logging

          router = APIRouter()

          @router.post("/row", response_class=HTMLResponse)
          async def handle_create_user_row(
              request: Request,
              user_in: schemas.UserCreate = Depends(schemas.UserCreate.as_form),
              db: Session = Depends(deps.get_db),
              templates: Jinja2Templates = Depends(deps.get_templates),
          ):
              try:
                  created_user = crud.user.create(db=db, obj_in=user_in)
                  user = crud.user.get_user_with_details(db, user_id=created_user.id)
                  if not user:
                      raise HTTPException(status_code=500, detail="Failed to retrieve user after creation")
              except ValueError as e:
                  return templates.TemplateResponse(
                      request=request,
                      name="components/common/form_error.html",
                      context={"error_message": str(e)},
                      status_code=status.HTTP_400_BAD_REQUEST
                  )
              except Exception as e:
                  return templates.TemplateResponse(
                      request=request,
                      name="components/common/form_error.html",
                      context={"error_message": "登録中にエラーが発生しました"},
                      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                  )

              return templates.TemplateResponse(
                  request=request,
                  name="components/user/_user_row.html",
                  context={"user": user},
                  status_code=status.HTTP_200_OK
              )
          ```
        - **`handle_update_user_row` (PUT `/pages/user/row/{user_id}`)**: `request: Request`, `user_id: int`, `user_in: schemas.UserUpdate = Depends(...)`, `db: Session` を引数に取り、内部で **共通化されたサービス関数/CRUD関数** (`user_service.update_user_with_validation` や `crud.user.update`) を呼び出す。成功後、更新された `user` を取得し、`TemplateResponse` で **新規作成した `components/user/_user_row.html`** をレンダリングして `HTMLResponse` (status_code=200) で返す。
            - 同様に `as_form` や `Form(...)` を利用。
        - **`get_user_edit_form` (GET `/pages/user/edit/{user_id}`)**: 編集モーダルの内容 (フォーム) をHTMLで返すエンドポイント。これも既存の `app/routers/pages/user.py` に追加する。
            - **新規作成するテンプレート (`components/user/_edit_form.html` など)** をレンダリングして返す。

3.  **フロントエンド テンプレート修正 (`app/templates/pages/user/index.html`):**
    - [ ] **テーブル `<tbody>` に ID (`id="user-table-body"`) を追加。**
    - [ ] **編集ボタン:** Alpine.js の `onclick` を削除し、代わりに `hx-get` を使用して編集フォームをモーダル内にロードするように変更。
        ```html
        <button class="btn btn-sm btn-outline"
                hx-get="{{ url_for('get_user_edit_form', user_id=user.id) }}" {# フォーム取得エンドポイント #}
                hx-target="#modal-content-edit-user-{{ user.id }}" {# モーダル内のコンテンツ領域 #}
                hx-swap="innerHTML"
                onclick="document.getElementById('edit-user-modal-{{ user.id }}').showModal()">
            編集
        </button>
        ```
        - 対応するモーダル (`edit_modal` マクロで生成される部分) 内に、フォームロード先のコンテナ (`id="modal-content-edit-user-{{ user.id }}"`) が存在することを確認。
    - [ ] **編集モーダル内フォーム (`components/user/_edit_form.html` など、上記 `hx-get` でロードされる部分):**
        - フォームタグに `hx-put="{{ url_for('handle_update_user_row', user_id=user.id) }}"` などを追加。
        - `hx-target="#user-row-{{ user.id }}"`
        - `hx-swap="outerHTML"`
        - `hx-indicator="#edit-modal-loading-{{ user.id }}"` (モーダル内のインジケータ)
        - `hx-on::after-request="if(event.detail.successful) { this.closest('dialog').close(); }"` (成功時にモーダルを閉じる)
        - フォーム内の保存ボタンから `data-*` 属性を削除。
        - モーダル内に `<span class="loading loading-spinner htmx-indicator" id="edit-modal-loading-{{ user.id }}"></span>` を追加。
    - [ ] **削除ボタン:** Alpine.js の `onclick` を削除し、`hx-delete` のみで動作するようにする (計画通り)。

4.  **JavaScript 修正 (`app/static/js/modal-handlers.js`):**
    - [ ] 社員管理の HTMX 化が完了したら、`updateUIAfterEdit` 関数内の `user-row-` ID を対象とした DOM 更新処理を削除。
    - [ ] `setupDeleteHandlers` 内の `fetch` と行削除処理が不要になったことを確認。
    - [ ] (全機能完了後) ファイル自体を削除。

## 7. 実施順序

1.  **社員管理 (`/user`)** で上記ステップ 1-4 を実施し、追加・編集・削除が HTMX で動作することを確認。エラーハンドリングも確認。
2.  問題がなければ、**グループ管理 (`/groups`)** で同様のステップを実施。
3.  **社員種別管理 (`/user_types`)** で同様のステップを実施。
4.  **勤務場所管理 (`/locations`)** で同様のステップを実施。
5.  すべての管理機能の HTMX 化が完了したら、`app/static/js/modal-handlers.js` と `app/static/js/apiClient.js` を削除し、`app/templates/layout/head.html` からこれらのスクリプト読み込みを削除する。関連するテストを実施する。

## 8. 考慮事項

- **エラーハンドリング:**
    - **バックエンド:**
        - **HTML 返却用 API (`/pages/*/row`)**: バリデーションエラーやDBエラー発生時、エンドポイントはエラーメッセージを含むHTMLフラグメント (例: **新規作成する** `components/common/form_error.html` をレンダリング) を `HTMLResponse(content=..., status_code=4xx)` で返す。
        - **JSON API (`/api/v1/*`)**: 従来通り JSON 形式でエラー情報を返す。
    - **フロントエンド:** HTMX フォーム要素に `hx-target="#form-error-message"` と `hx-swap="outerHTML"` を追加するか、`HX-Retarget` レスポンスヘッダーをバックエンドから送信して、エラー表示領域を指定する。モーダルを閉じないように、エラー時の `hx-on::after-request` 処理はスキップさせる (`if(event.detail.successful)` の条件分岐が役立つ)。エラーメッセージ表示用のコンテナ (`<div id="form-error-message"></div>`) をモーダル内に配置する。
- **ローディングインジケータ:** `htmx-indicator` クラスと `hx-indicator` 属性を活用し、処理中のフィードバックをユーザーに提供する。
- **URL生成:** テンプレート内では FastAPI の `url_for()` を使用する。そのためには、ページをレンダリングするエンドポイント (`app/routers/pages/*.py` 内) で `request: Request` を受け取り、`TemplateResponse` のコンテキストに `{\"request\": request, ...}` を含める必要がある。APIエンドポイント関数名を正しく指定すること。（FastAPI 0.100.0 以降は `TemplateResponse(request=request, name=...)` の形式が推奨）
- **Alpine.js との連携:** モーダルの表示 (`*.showModal()`) は `onclick` で残すのがシンプル。HTMXリクエスト成功後のモーダル非表示 (`*.close()`) は `hx-on::after-request` で実装する。これら以外の複雑な連携は必要に応じて検討。
- **スキーマとフォーム:** `Depends(Schema.as_form)` を利用する場合、対象スキーマに `as_form` クラスメソッドを定義する必要がある点に注意。
- **テスト:** リファクタリング後は、各管理機能の追加・編集・削除が期待通りに動作することを手動テストで確認する。**JSON API と HTML API の両方に対する自動テストを追加・更新**し、コアロジックの変更が両方に反映されることを担保する。 