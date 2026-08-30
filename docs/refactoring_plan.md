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
        - **DELETE:** 現状、ユーザー管理 (`/api/v1/users/{id}`) は成功時に 204 No Content を返すが、他の管理機能は異なる可能性があるため、**204 No Content に統一する必要がある**。
    - CRUD 操作は `app/crud/*.py` 内の関数で行われる (`CRUDBase` を継承)。
    - HTML ページを提供するエンドポイントは `app/routers/pages/*.py` に存在する。
    - **サービス層 (`app/services/*.py`) は現状存在しない**。ビジネスロジック (バリデーション等) は API ルーター内に記述されている。

## 4. リファクタリング方針

**基本戦略として、外部システム連携用の JSON API (`/api/v1/*`, 実装は `app/routers/api/v1/*.py`) は維持し、UI 部分更新用の HTML フラグメント API (`/pages/*`, 実装は `app/routers/pages/*.py`) を追加・修正します。両者は明確に分離しつつ、データベース操作は `app/crud/` 層、ビジネスロジックは**新規作成する** `app/services/` 層で実装し、コードの重複を避けます。**

- **API エンドポイント戦略:**
    - **JSON API (`/api/v1/<entity>`)**: **データ操作と外部システム連携** を主目的とし、原則として JSON 形式でレスポンスを返す。実装は `app/routers/api/v1/<entity>.py`。既存の仕様を維持する。
    - **HTML フラグメント API (`/pages/<entity>/row` 等)**: **Web UI (HTMX) からの部分更新** を目的とし、HTML フラグメント (`<tr>` 等) を `HTMLResponse` で返す。実装は `app/routers/pages/<entity>.py` に**追加**する。
    - **DELETE API (`/api/v1/<entity>/{id}`)**: 削除操作はシンプルであるため、既存の `/api/v1/*` (実装: `app/routers/api/v1/<entity>.py`) を流用し、成功時に `Response(status_code=204)` を返すように統一する (HTMX は空レスポンスで要素削除が可能)。**ユーザー管理 API は既にこの形式のため、他の管理機能 API を修正する。**
    - **コアロジック共通化**: HTML 返却用 API は、内部で既存の JSON API と同じ **`app/crud/` 関数** や **新規作成する `app/services/` 関数** (バリデーション等) を呼び出し、コアロジックの重複を徹底的に避ける。
    - **コアロジック共通化の徹底 (重要):**
        - **CRUD操作:** データベースへの実際の読み書き (Create, Read, Update, Delete) は、`app/crud/*.py` 内の関数 (`CRUDBase` を利用) に集約する。JSONを返すAPI (`app/routers/api/v1/*.py`) もHTMLを返すAPI (`app/routers/pages/*.py`) も、**必ず同じCRUD関数を呼び出す**こと。
            - 例 (`app/crud/user.py` の `update`): `CRUDBase.update` を利用するため、`UserUpdate` スキーマを受け取り、更新後の `User` オブジェクトを返すインターフェースになっているはず（要 `app/crud/base.py` の実装確認）。このため、`app/crud/user.py` 自体のリファクタリングは不要な可能性が高い。
        - **データ取得:** APIが必要とするデータ（リレーション含む）を取得するロジックも共通化する。HTMLフラグメント生成やJSONレスポンス生成に必要な関連データ（グループ名、社員種別名など）が効率的に取得できるように、**`app/crud/<entity>.py` に専用の取得関数 (`get_<entity>_with_details` など) を追加するか、新規作成する `app/services/<entity>_service.py` で取得ロジックを実装**する。
        - **ビジネスロジック/権限チェック:** 単純なCRUD以上のロジックや権限チェックは、**新規作成する `app/services/*.py`** に切り出し、両方のエンドポイントタイプから呼び出す。既存の API ルーター (`app/routers/api/v1/*.py`) 内のロジックは、このサービス関数呼び出しに置き換える。
            - 例 (`app/routers/api/v1/user.py` 内のグループ・社員種別存在チェック): **新規作成する `app/services/user_service.py`** に `validate_user_dependencies` や `create_user_with_validation` といったサービス関数を作成し、そこへロジックを移動させる。
- **部分テンプレートの活用:**
    - テーブル行 (`<tr>`) を表示するための部分テンプレートを `app/templates/components/<entity>/` ディレクトリ (例: `app/templates/components/user/`) を**新規作成**し、その中に `_<entity>_row.html` (例: `_user_row.html`) として配置する。
    - 編集フォーム用の部分テンプレートも同様に `app/templates/components/<entity>/_<entity>_edit_form.html` (例: `_user_edit_form.html`) として配置する。
    - 共通のエラー表示用テンプレートは `app/templates/components/common/_form_error.html` を**新規作成**して利用する。

## 5. 対象となる管理機能

- [ ] 社員管理 (`/user`)
- [ ] グループ管理 (`/groups`)
- [ ] 社員種別管理 (`/user_types`)
- [ ] 勤務場所管理 (`/locations`)

## 6. 作業ステップ (各管理機能ごと)

以下は **社員管理 (`/user`)** を例とした具体的な作業ステップ。他の管理機能 (`group`, `user_type`, `location`) も同様の手順で実施する。ファイルパスの `<entity>` 部分を適宜読み替える。

1.  **部分テンプレート作成 (`app/templates/components/user/`):**
    - [ ] 新規に `app/templates/components/user/` ディレクトリを作成する。
    - [ ] `app/templates/pages/user/index.html` 内のユーザーテーブルの `<tr>...</tr>` 部分を参考に `app/templates/components/user/_user_row.html` を**新規作成**。`user` オブジェクトをコンテキスト変数として受け取る。
        ```html
        {# app/templates/components/user/_user_row.html #}
        <tr id="user-row-{{ user.id }}">
            {# ... 各セル (td) の内容 ... #}
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
                        hx-indicator="#row-indicator-{{ user.id }}">
                    削除
                </button>
                <span class="loading loading-spinner loading-xs htmx-indicator" id="row-indicator-{{ user.id }}"></span>
            </td>
        </tr>
        ```
    - [ ] 編集モーダル用のフォーム部分テンプレート `app/templates/components/user/_user_edit_form.html` を**新規作成**。`user` オブジェクトと関連データ (グループリスト等) を受け取る。HTMX属性 (hx-put, hx-target, hx-swap など) をフォームタグに付与する。
    - [ ] `app/templates/pages/user/index.html` のテーブルループを修正し、`{% include "components/user/_user_row.html" with context %}` を使用するように変更。テーブルの `<tbody>` に `id="user-table-body"` を付与。編集モーダルのコンテンツ部分 (`<div id="modal-content-edit-user-{{ user.id }}">`) を用意。
    - [ ] **新規**に共通のエラー表示用テンプレート `app/templates/components/common/_form_error.html` を作成する。
        ```html
        {# app/templates/components/common/_form_error.html #}
        <div class="text-error p-2 border border-error rounded-md my-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6 inline-block mr-2" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>{{ error_message }}</span>
        </div>
        ```

2.  **バックエンド API 修正:**
    - [ ] **サービス層の作成:**
        - [ ] **新規** に `app/services/` ディレクトリを作成する。
        - [ ] **新規** に `app/services/user_service.py` ファイルを作成し、`app/routers/api/v1/user.py` 内のグループ・社員種別存在チェックなどのビジネスロジックを共通のサービス関数 (`validate_user_dependencies` など) に切り出す。作成 (`create_user_with_validation`) や更新 (`update_user_with_validation`) 用のサービス関数も実装し、CRUD呼び出し前にこのバリデーションを呼び出すようにする。
    - [ ] **CRUD 層の修正 (必要に応じて):**
        - [ ] HTMLフラグメント生成に必要な関連データ (グループ名、社員種別名) を含めてユーザー情報を取得する関数 `get_user_with_details(db: Session, user_id: str) -> Optional[User]` を `app/crud/user.py` に**追加**するか、`app/services/user_service.py` 内で実装する。
    - [ ] **既存 `app/routers/api/v1/user.py` の修正:**
        - **`delete_user` (DELETE `/api/v1/users/{user_id}`)**: 現状で `Response(status_code=204)` を返しているため、**修正不要**。
        - `create_user` (POST), `update_user` (PUT): 内部のビジネスロジックを**新規作成した** `app/services/user_service.py` のサービス関数 (`user_service.validate_user_dependencies` や `user_service.create/update_user_with_validation`) の呼び出しに置き換える。
    - [ ] **既存 `app/routers/pages/user.py` にエンドポイント追加:**
        - **コアロジック共通化の確認:** 以下の新規エンドポイントを実装する前に、関連する `app/crud/user.py` 関数や**新規作成した `app/services/user_service.py`** が適切に利用可能か確認する。
        - **`handle_create_user_row` (POST `/pages/user/row`)**: `request: Request`, `user_in: schemas.UserCreate = Depends(schemas.UserCreate.as_form)`, `db: Session`, `templates: Jinja2Templates` を引数に取り、内部で**共通化されたサービス関数/CRUD関数** (例: `app/services/user_service.py` の `create_user_with_validation` や `app/crud/user.py` の `create`) を呼び出す。成功後、**追加した `app/crud/user.py` の `get_user_with_details`** などで作成された `user` を取得し、`TemplateResponse` で**新規作成した `app/templates/components/user/_user_row.html`** をレンダリングして `HTMLResponse` (status_code=200) で返す。
            - このエンドポイントを動作させるには、`app/schemas/user.py` の `UserCreate` スキーマに `as_form` クラスメソッドを**実装する必要がある**。
          ```python
          # 例: app/routers/pages/user.py (既存ファイルに追加)
          from fastapi import APIRouter, Depends, Request, status, HTTPException, Form # Formを追加
          from fastapi.responses import HTMLResponse
          from fastapi.templating import Jinja2Templates
          from sqlalchemy.orm import Session
          from app.db import deps
          from app import crud, schemas, services # services をインポート
          # from app.core.config import settings # 不要なら削除
          # from app.core.logging_config import setup_logging # 不要なら削除

          router = APIRouter()

          @router.post("/row", response_class=HTMLResponse)
          async def handle_create_user_row(
              request: Request,
              # スキーマに実装された as_form を使ってフォームデータを受け取る
              user_in: schemas.UserCreate = Depends(schemas.UserCreate.as_form),
              db: Session = Depends(deps.get_db),
              templates: Jinja2Templates = Depends(deps.get_templates),
          ):
              try:
                  # サービス層でバリデーションと作成を行う例
                  created_user = await services.user_service.create_user_with_validation(db=db, user_in=user_in)
                  # CRUD層で詳細情報を取得する例
                  user = crud.user.get_user_with_details(db, user_id=created_user.id)
                  if not user:
                      # このケースは通常発生しないはずだが念のため
                      raise HTTPException(status_code=500, detail="Failed to retrieve user after creation")
              except ValueError as e: # サービス層がバリデーションエラー時にValueErrorをraiseすると仮定
                  # エラーメッセージを含むフォームエラーコンポーネントを返す
                  return templates.TemplateResponse(
                      request=request,
                      name="app/templates/components/common/_form_error.html",
                      context={"error_message": str(e)},
                      status_code=status.HTTP_400_BAD_REQUEST
                  )
              except HTTPException as e:
                  # サービス層やCRUD層がHTTPExceptionをraiseする場合
                  return templates.TemplateResponse(
                      request=request,
                      name="app/templates/components/common/_form_error.html",
                      context={"error_message": e.detail},
                      status_code=e.status_code
                  )
              except Exception as e: # 予期せぬエラー
                  # logging.exception(e) # エラーログ推奨
                  return templates.TemplateResponse(
                      request=request,
                      name="app/templates/components/common/_form_error.html",
                      context={"error_message": "登録中に予期せぬエラーが発生しました"},
                      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                  )

              # 成功時は新しい行のHTMLを返す
              return templates.TemplateResponse(
                  request=request,
                  name="app/templates/components/user/_user_row.html",
                  context={"user": user},
                  status_code=status.HTTP_200_OK # 成功時は200 OK
              )
          ```
        - **`handle_update_user_row` (PUT `/pages/user/row/{user_id}`)**: 同様に `request`, `user_id`, `db`, `templates` と `user_in: schemas.UserUpdate = Depends(schemas.UserUpdate.as_form)` を引数に取る。内部で**共通化されたサービス/CRUD関数** (例: `app/services/user_service.py`, `app/crud/user.py`) を呼び出す。成功後、更新された `user` データを使って**新規作成した `app/templates/components/user/_user_row.html`** をレンダリングし `HTMLResponse` (status_code=200) で返す。エラーハンドリングも `_form_error.html` を使用する。(`UserUpdate` スキーマにも `as_form` の実装が必要)。
        - **`get_user_edit_form` (GET `/pages/user/edit/{user_id}`)**: `request`, `user_id`, `db`, `templates` を引数に取る。`app/crud/user.py` の `get_user_with_details` でユーザー情報を取得し、グループリスト等も `app/crud/` から取得する。これらのデータをコンテキストとして**新規作成した `app/templates/components/user/_user_edit_form.html`** をレンダリングして `HTMLResponse` で返す。

3.  **フロントエンド テンプレート修正 (`app/templates/pages/user/index.html`):**
    - [ ] **テーブル `<tbody>` に ID (`id="user-table-body"`) を追加。**
    - [ ] **編集ボタン:** `hx-get` で編集フォームをロードする設定は計画通り。対応するモーダル内にフォームロード先のコンテナ (`id="modal-content-edit-user-{{ user.id }}"`) があることを確認。
        ```html
        <button class="btn btn-sm btn-outline"
                hx-get="{{ url_for('get_user_edit_form', user_id=user.id) }}"
                hx-target="#modal-content-edit-user-{{ user.id }}"
                hx-swap="innerHTML"
                onclick="document.getElementById('edit-user-modal-{{ user.id }}').showModal()">
            編集
        </button>
        {# 対応するモーダル #}
        <dialog id="edit-user-modal-{{ user.id }}" class="modal">
            <div class="modal-box w-11/12 max-w-5xl">
                <h3 class="font-bold text-lg">ユーザー編集</h3>
                {# フォームはこの中にロードされる #}
                <div id="modal-content-edit-user-{{ user.id }}">
                    <span class="loading loading-spinner"></span> {# 初期ローディング表示 #}
                </div>
                <div class="modal-action">
                    <form method="dialog">
                        <button class="btn">閉じる</button>
                    </form>
                </div>
            </div>
        </dialog>
        ```
    - [ ] **編集モーダル内フォーム (新規作成する `app/templates/components/user/_user_edit_form.html`):**
        - フォームタグに `hx-put="{{ url_for('handle_update_user_row', user_id=user.id) }}\"` 等、計画通りの HTMX 属性を追加。
        - `hx-target="#user-row-{{ user.id }}\"`
        - `hx-swap="outerHTML"`
        - モーダル内にインジケータ用の要素 (`<span class="loading loading-spinner htmx-indicator" id="edit-modal-indicator-{{ user.id }}"></span>`) とエラーメッセージ表示用の要素 (`<div id="edit-form-error-{{ user.id }}"></div>`) を配置し、`hx-indicator` とエラー時の `hx-target` (またはバックエンドからの `HX-Retarget`) でこれらを指定するようにする。
        - `hx-on::after-request="if(event.detail.successful) { document.getElementById('edit-user-modal-{{ user.id }}').close(); }"` を追加。
        - フォーム内の保存ボタンから JavaScript 関連の `data-*` 属性を削除。
    - [ ] **削除ボタン:** `hx-delete` の設定は計画通り。
    - [ ] **追加モーダル内フォーム (例: `app/templates/components/user/_user_add_form.html` など既存または新規作成):**
        - フォームタグに `hx-post="{{ url_for('handle_create_user_row') }}\"`
        - `hx-target="#user-table-body"`
        - `hx-swap="beforeend"`
        - 同様にインジケータとエラー表示領域 (`hx-indicator`, `hx-target` / `HX-Retarget`) を設定。
        - `hx-on::after-request="if(event.detail.successful) { this.reset(); document.getElementById('add-user-modal').close(); }"`
        - JavaScript 関連の `data-*` 属性を削除。

4.  **JavaScript 修正 (`app/static/js/modal-handlers.js`):**
    - [ ] 社員管理の HTMX 化が完了したら、`updateUIAfterEdit` 関数内の `user-row-` ID を対象とした DOM 更新処理を削除。
    - [ ] `setupAddFormHandler`, `setupEditFormHandlers`, `setupDeleteHandlers` からユーザー管理に関連する `fetch` 呼び出しと DOM 操作ロジックを削除。
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
        - **HTML 返却用 API (`/pages/*/row`, `/pages/*/edit`)**: バリデーションエラーやDBエラー発生時、エンドポイントはエラーメッセージを含むHTMLフラグメント (例: **新規作成する** `components/common/_form_error.html` をレンダリング) を `HTMLResponse(content=..., status_code=4xx)` で返す。
        - **JSON API (`/api/v1/*`)**: 従来通り JSON 形式でエラー情報を返す。
    - **フロントエンド:** HTMX フォーム要素に `hx-target="#form-error-message"` (エラー表示領域のID) と `hx-swap="outerHTML"` を追加するか、バックエンドから `HX-Retarget` レスポンスヘッダーを送信してエラー表示領域を指定する。エラーメッセージ表示用のコンテナ (`<div id="form-error-message"></div>`) をモーダル内のフォーム付近に配置する。`hx-on::after-request` の `if(event.detail.successful)` 条件により、エラー時はモーダルが閉じないようにする。
- **ローディングインジケータ:** `htmx-indicator` クラスと `hx-indicator` 属性を活用し、処理中のフィードバックをユーザーに提供する。各フォーム送信ボタンの近くや、更新対象のテーブル行にインジケータを配置する。
- **URL生成:** テンプレート内では FastAPI の `url_for()` を使用する。`TemplateResponse` のコンテキストに `{\"request\": request, ...}` を含める (FastAPI 0.100.0 以降は `TemplateResponse(request=request, name=...)` が推奨)。
- **Alpine.js との連携:** モーダルの表示 (`*.showModal()`) は `onclick` で残す。HTMXリクエスト成功後のモーダル非表示 (`*.close()`) は `hx-on::after-request` で実装。
- **スキーマとフォーム:** HTMX フォームからのデータ受け取りには、Pydantic スキーマに `as_form` クラスメソッドを**実装する**か、エンドポイントのシグネチャで `fastapi.Form(...)` を使用する。どちらの方法を選択するか一貫性を持たせる。
- **テスト:** リファクタリング後は、各管理機能の追加・編集・削除が HTMX で期待通りに動作することを手動テストで確認する。**JSON API と HTML API の両方に対する自動テストを追加・更新**し、コアロジックの変更が両方に反映されることを担保する。特にサービス層のロジックに対するテストを充実させる。 