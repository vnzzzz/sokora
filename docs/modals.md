# モーダルコンポーネント

## 概要

Sokoraアプリケーションでは、社員管理、グループ管理、社員種別管理、勤務場所管理などの画面で使われるモーダルを共通化しています。これにより、コードの重複を避け、保守性を向上させるとともに、モーダルの動作を統一しています。

## 共通モーダルコンポーネント

共通モーダルは `app/templates/components/common/modal.html` に以下の3種類のマクロとして実装されています：

1. **add_modal** - 新規追加用のモーダル
2. **edit_modal** - 編集用のモーダル
3. **delete_confirm_modal** - 削除確認用のモーダル

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
  
  <!-- マクロを呼び出してモーダルを表示 -->
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
  
  <!-- マクロを呼び出してモーダルを表示 -->
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
  {% set delete_warning %}
  ※関連データが存在する場合は削除できません。
  {% endset %}
  
  <!-- マクロを呼び出してモーダルを表示 -->
  {{ delete_confirm_modal("削除の確認", delete_warning, item.id, item.name) }}
</div>
```

## 共通スクリプト

モーダル操作に関する共通のJavaScriptは `app/static/js/modal-handlers.js` に実装されています。
これには以下の関数が含まれます：

1. **setupAddFormHandler** - 追加フォームの送信処理を設定
2. **setupEditFormHandlers** - 編集フォームの送信処理を設定
3. **setupDeleteHandlers** - 削除ボタンの処理を設定

### 使用例

スクリプト部分で以下のように使用します：

```html
{% block extra_scripts %}
<script src="/static/js/modal-handlers.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    // 追加処理の設定
    setupAddFormHandler('form-id', '/api/endpoint/');
    
    // 編集処理の設定
    setupEditFormHandlers('.edit-button-selector', 'edit-form', '/api/endpoint/{id}');
    
    // 削除処理の設定
    setupDeleteHandlers('.delete-button-selector', '/api/endpoint/{id}');
  });
</script>
{% endblock %}
```

## 実装例

社員種別管理ページ（`app/templates/pages/user_type/index.html`）では、共通モーダルコンポーネントを使用して実装されています。このファイルを参考にして他の管理ページも同様に実装することができます。

## 技術スタック

- Alpine.js - モーダルの表示/非表示の状態管理
- Tailwind CSS / DaisyUI - モーダルのスタイリング
- Jinja2テンプレート - マクロによるコンポーネント化
- Fetch API - APIとの非同期通信

## 利点

1. **保守性の向上** - モーダルのコードが一箇所に集約されるため、変更が必要な場合も一箇所の修正で済みます
2. **一貫性の確保** - すべての画面で同じモーダルUIと動作を提供します
3. **コードの重複削減** - 同じモーダルコードを複数の場所にコピー&ペーストする必要がなくなります
4. **開発効率の向上** - 新しい画面を作成する際に、既存のモーダルコンポーネントを再利用できます 