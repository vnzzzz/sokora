document.addEventListener('DOMContentLoaded', () => {
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
    })
  }

  // --- サイドバーのアクティブメニューハイライト ---
  function highlightActiveSidebarLink() {
    const currentPath = window.location.pathname
    const menuLinks = document.querySelectorAll('aside a') // セレクタをaside内に限定

    menuLinks.forEach((link) => {
      const linkPath = link.getAttribute('href')

      // 既存のアクティブクラスを念のため削除
      link.classList.remove('bg-base-300', 'font-medium')
      link.classList.add('btn-ghost') // デフォルトに戻す

      // 完全一致の場合
      if (currentPath === linkPath) {
        link.classList.add('bg-base-300', 'font-medium')
        link.classList.remove('btn-ghost')
        return // 次のリンクへ
      }

      // パスの先頭一致（サブページの場合）
      // 例: /user/1 は /user にマッチ
      if (linkPath !== '/' && currentPath.startsWith(linkPath + '/')) {
        link.classList.add('bg-base-300', 'font-medium')
        link.classList.remove('btn-ghost')
      } else if (linkPath !== '/' && currentPath.startsWith(linkPath) && linkPath.split('/').length > 1) {
        // /user_types など、/ が含まれる場合で末尾に / がない場合も考慮
        // より深い階層への完全一致を防ぐため、単純な startsWith だけでは不十分な場合がある
        // （例: /users と /users/create がある場合、/users/create のときに /users がアクティブにならないように）
        // ただし、現在のロジックでは /user も /user_types も / で始まるため、より洗練されたマッチングが必要になる可能性がある
        // 一旦、シンプルな startsWith + '/' を維持
      }
    })
  }

  // DOMContentLoaded時とHTMXによるナビゲーション後にハイライトを実行
  highlightActiveSidebarLink() // 初期表示時に実行
  document.body.addEventListener('htmx:navigated', highlightActiveSidebarLink) // HTMXナビゲーション後に実行

  // --- Alpine.js 初期化 ---
  // base.html から移動
  document.addEventListener('alpine:init', () => {
    // ダークモード設定を適用
    applyDarkModePreference()
  })
})
