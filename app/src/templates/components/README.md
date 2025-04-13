# テンプレートコンポーネントの使用方法

## 概要

このディレクトリには再利用可能な HTML コンポーネントが含まれています。コンポーネントは`{% include %}`タグを使用して他の
テンプレートから組み込むことができます。

## 使用方法

### head.html

ページの`<head>`部分を提供します。タイトルをカスタマイズすることができます。

```jinja
{% set title_text = "ページタイトル" %}
{% include "components/head.html" %}
```

title_text を指定しない場合は、デフォルトで "Sokora" が使用されます。

### navbar.html

アプリケーションのナビゲーションバーを提供します。

```jinja
{% include "components/navbar.html" %}
```

### theme_switcher.html

ライトモードとダークモードを切り替えるボタンを提供します。

```jinja
{% include "components/theme_switcher.html" %}
```

### csv_upload_modal.html

CSV アップロードのためのモーダルダイアログを提供します。Alpine.js のグローバルストアを使用しています。

```jinja
{% include "components/csv_upload_modal.html" %}
```

モーダルを表示するには以下の JavaScript が必要です：

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.store('importModal', {
    open: false,
    toggle() {
      this.open = !this.open
    }
  })
})
```

トグルボタンには以下の属性を設定します：

```html
<button @click="$store.importModal.toggle()">CSVアップロード</button>
```
