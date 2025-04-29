# モーダルコンポーネント

## 概要

Sokoraアプリケーションでは、社員管理、グループ管理、社員種別管理、勤務場所管理などの画面で使われるモーダルを共通化しています。これにより、コードの重複を避け、保守性を向上させるとともに、モーダルの動作を統一しています。

## 共通モーダルコンポーネント

共通モーダルは `app/templates/components/common/modal.html` に以下の3種類のマクロとして実装されています：

1.  **add_modal(title, form_id, content_block, submit_btn_text="追加")** - 新規追加用のモーダル
2.  **edit_modal(title, form_id, content_block, item_id, btn_color_class="", submit_btn_text="保存")** - 編集用のモーダル
3.  **delete_confirm_modal(title, content_block, item_id, item_name, submit_btn_text="削除")** - 削除確認用のモーダル

-   `title`: モーダルのタイトル
-   `form_id`: モーダル内のフォームのID（編集・削除時はitem\_idと組み合わせて使われることが多い）
-   `content_block`: モーダル内に表示するフォーム要素などのHTMLコンテンツ（Jinja2の `{% set %}` で定義）
-   `submit_btn_text` (オプション): 送信ボタンのテキスト（デフォルト値あり）
-   `item_id`: 編集・削除対象のアイテムID
-   `item_name`: 削除確認メッセージに表示するアイテム名
-   `btn_color_class` (オプション): モーダルタイトルの色クラス（例: "text-error"）

## 使用方法

### 1. モーダルコンポーネントのインポート

テンプレートの先頭で必要なモーダルマクロをインポートします。

```html
{% from "components/common/modal.html" import add_modal, edit_modal, delete_confirm_modal %}
```

### 2. 追加モーダルの使用例

```html
<!-- Alpine.jsでモーダルの表示/非表示を制御 -->
<div x-data="{ showAddModal: false }" @click.away="showAddModal = false">
  <button @click="showAddModal = true" class="btn btn-sm btn-outline">
    追加
  </button>

  <!-- 追加モーダルの内容を定義 -->
  {% set add_content %}
  <div class="form-control">
    <label class="label" for="add-name">
      <span class="label-text">名前</span>
    </label>
    <input
      type="text"
      id="add-name"
      name="name"
      class="input input-bordered w-full"
      required
    />
  </div>
  {% endset %}

  <!-- マクロを呼び出してモーダルを表示 (ボタンテキストはデフォルトの「追加」) -->
  {{ add_modal("追加タイトル", "add-form-id", add_content) }}
</div>
```

### 3. 編集モーダルの使用例

```html
<div x-data="{ showEditModal: false }">
  <button @click="showEditModal = true" class="btn btn-sm btn-outline">
    編集
  </button>

  <!-- 編集モーダルの内容を定義 -->
  {% set edit_content %}
  <div class="form-control">
    <label class="label" for="edit-name-{{ item.id }}">
      <span class="label-text">名前</span>
    </label>
    <input
      type="text"
      id="edit-name-{{ item.id }}"
      name="name"
      value="{{ item.name }}"
      class="input input-bordered"
      required
    />
  </div>
  {% endset %}

  <!-- マクロを呼び出してモーダルを表示 (ボタンテキストはデフォルトの「保存」) -->
  {{ edit_modal("編集タイトル", "edit-form", edit_content, item.id) }}
</div>
```

### 4. 削除確認モーダルの使用例

```html
<div x-data="{ showDeleteConfirm: false }">
  <button @click="showDeleteConfirm = true" class="btn btn-sm btn-error btn-outline">
    削除
  </button>

  <!-- 削除確認の追加警告メッセージを定義 -->
  {% set delete_content %}
  <p class="text-warning">※関連データが存在する場合は削除できません。</p>
  {% endset %}

  <!-- マクロを呼び出してモーダルを表示 (ボタンテキストを「削除する」に変更) -->
  {{ delete_confirm_modal("削除の確認", delete_content, item.id, item.name, submit_btn_text="削除する") }}
</div>
```

## 共通スクリプト

モーダル操作に関する共通のJavaScriptは `app/static/js/modal-handlers.js` に実装されています。
これには以下の主要な関数が含まれます：

1.  **setupAddFormHandler(formId, endpoint, redirectUrl = null, successCallback = null)** - 追加フォームの送信処理を設定
    -   `formId`: 追加フォームのID
    -   `endpoint`: 送信先のAPIエンドポイント
    -   `redirectUrl` (オプション): 成功時にリダイレクトするURL。指定しない場合、デフォルトでページリロード。
    -   `successCallback` (オプション): 成功時に実行するコールバック関数。`redirectUrl` より優先される。
2.  **setupEditFormHandlers(selector, formIdPrefix, endpointTemplate, successCallback = null)** - 編集フォームの送信処理を設定
    -   `selector`: 編集モーダル内の送信ボタンを特定するCSSセレクタ (例: `.btn[data-item-id][class*="btn-neutral"]`)
    -   `formIdPrefix`: 編集フォームのID接頭辞 (例: `edit-form`)。フォームIDは `${formIdPrefix}-${itemId}` となる。
    -   `endpointTemplate`: 送信先のAPIエンドポイントテンプレート (例: `/api/endpoint/{id}`)
    -   `successCallback` (オプション): 成功時に実行するコールバック関数。引数として `(responseData, itemId)` を受け取る。デフォルトでは `updateUIAfterEdit` が呼ばれ、テーブルなどのUIを更新する。
3.  **setupDeleteHandlers(selector, endpointTemplate, successCallback = null)** - 削除ボタンの処理を設定
    -   `selector`: 削除確認モーダル内の送信ボタンを特定するCSSセレクタ (例: `.btn[data-item-id][class*="btn-error"]`)
    -   `endpointTemplate`: 送信先のAPIエンドポイントテンプレート (例: `/api/endpoint/{id}`)
    -   `successCallback` (オプション): 成功時に実行するコールバック関数。引数として `(responseData, itemId)` を受け取る。

### 使用例

テンプレートの `<script>` タグ内で以下のように使用します：

```html
{% block extra_scripts %}
<script src="/static/js/modal-handlers.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    // 追加処理の設定 (成功したらページリロード)
    setupAddFormHandler('add-form-id', '/api/items/');

    // 編集処理の設定 (成功したらデフォルトのUI更新 + モーダル閉じ)
    // 送信ボタンは btn-neutral で data-item-id 属性を持つものを対象とする
    setupEditFormHandlers('.btn[data-item-id][class*="btn-neutral"]', 'edit-form', '/api/items/{id}');

    // 削除処理の設定 (成功したらテーブルから行を削除)
    // 送信ボタンは btn-error で data-item-id 属性を持つものを対象とする
    setupDeleteHandlers('.btn[data-item-id][class*="btn-error"]', '/api/items/{id}', function(data, itemId) {
      // 成功したら該当行を削除
      const row = document.getElementById('item-row-' + itemId);
      if (row) {
        const tbody = row.closest('tbody');
        row.remove();
        // テーブルが空になったらリロードするなどの処理も可能
        if (tbody && tbody.children.length === 0) {
           window.location.reload();
        }
      }
    });
  });
</script>
{% endblock %}
```

## 実装例

社員種別管理ページ（`app/templates/pages/user_type/index.html`）や、グループ管理 (`group/index.html`)、勤務場所管理 (`location/index.html`)、社員管理 (`user/index.html`) などで、共通モーダルコンポーネントとスクリプトハンドラが使用されています。これらのファイルを参考にして他の管理ページも同様に実装することができます。

## 技術スタック

-   Alpine.js - モーダルの表示/非表示の状態管理
-   Tailwind CSS / DaisyUI - モーダルのスタイリング
-   Jinja2テンプレート - マクロによるコンポーネント化
-   Fetch API (`js/api-client.js` 経由) - APIとの非同期通信

## 利点

1.  **保守性の向上** - モーダルのコードが一箇所に集約されるため、変更が必要な場合も一箇所の修正で済みます
2.  **一貫性の確保** - すべての画面で同じモーダルUIと動作を提供します
3.  **コードの重複削減** - 同じモーダルコードを複数の場所にコピー&ペーストする必要がなくなります
4.  **開発効率の向上** - 新しい画面を作成する際に、既存のモーダルコンポーネントを再利用できます 