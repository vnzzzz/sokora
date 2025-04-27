document.addEventListener('DOMContentLoaded', () => {
  // console.log('sokora main.js loaded')

  // テーマ切り替え機能
  const themeToggle = document.getElementById('theme-toggle')
  if (themeToggle) {
    // ローカルストレージからテーマを復元
    const savedTheme = localStorage.getItem('theme') || 'light'

    // HTML要素とbody要素の両方にdata-theme属性を設定
    document.documentElement.setAttribute('data-theme', savedTheme)
    document.body.setAttribute('data-theme', savedTheme)

    // トグルボタンの初期状態を設定
    themeToggle.checked = savedTheme === 'dark'

    // テーマ切り替えイベント
    themeToggle.addEventListener('change', function () {
      const newTheme = this.checked ? 'dark' : 'light'

      // HTML要素とbody要素の両方のdata-theme属性を更新
      document.documentElement.setAttribute('data-theme', newTheme)
      document.body.setAttribute('data-theme', newTheme)

      // ローカルストレージに保存
      localStorage.setItem('theme', newTheme)

      // テーマ変更イベントを発火（必要に応じて他のコンポーネントに通知）
      document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }))

      console.log('テーマを変更しました:', newTheme)
    })
  }
})
