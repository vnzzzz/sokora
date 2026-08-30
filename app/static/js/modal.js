/* eslint-env browser */
/* globals htmx */
;(function () {
  'use strict'

  /**
   * 現在表示中の月を取得する
   * @returns {string|null} YYYY-MM形式の月、または取得できない場合はnull
   */
  function getCurrentMonth() {
    // localStorageから取得
    return localStorage.getItem('selectedMonth')
  }

  /**
   * 表示中の月を保存する
   * @param {string} month - YYYY-MM形式の月
   */
  function saveCurrentMonth(month) {
    if (month) {
      localStorage.setItem('selectedMonth', month)
    }
  }

  /**
   * URLから月情報を抽出して保存
   */
  function saveMonthFromUrl() {
    const urlParams = new URLSearchParams(window.location.search)
    const monthParam = urlParams.get('month')
    if (monthParam) {
      saveCurrentMonth(monthParam)
    }
  }

  // 連続更新リクエストの管理用キュー
  // 複数のリクエストが短時間で来た場合に最新のリクエストだけを処理する
  let calendarUpdateQueue = []
  let calendarUpdateTimer = null

  /**
   * #calendar を丸ごと再取得して置き換える
   * @param {string|null} month - YYYY-MM
   */
  function refreshCalendar(month) {
    // もしmonthがnullなら現在保存されている月を使用
    if (!month) {
      month = getCurrentMonth()
    } else {
      // 新しい月を保存
      saveCurrentMonth(month)
    }

    // 新しいリクエストをキューに追加
    calendarUpdateQueue.push(month)

    // 既存のタイマーがあればキャンセル
    if (calendarUpdateTimer) {
      clearTimeout(calendarUpdateTimer)
    }

    // 短時間に複数のリクエストが来た場合、最後のリクエストのみを処理
    calendarUpdateTimer = setTimeout(() => {
      // キューの最後のリクエストを取得
      const latestMonth = calendarUpdateQueue[calendarUpdateQueue.length - 1]

      // キューをクリア
      calendarUpdateQueue = []
      calendarUpdateTimer = null

      // 実際の更新処理を実行
      executeCalendarUpdate(latestMonth)
    }, 200)
  }

  /**
   * 実際のカレンダー更新処理を実行
   * @param {string|null} month - YYYY-MM
   */
  function executeCalendarUpdate(month) {
    // カレンダー更新処理中フラグ
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    // リクエスト中フラグをセット
    window.calendarRefreshInProgress = true

    const url = month ? `/attendance?month=${encodeURIComponent(month)}` : '/attendance'

    // htmxリクエスト完了イベントのリスナーを定義
    const afterSwapListener = function (event) {
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterSwap', afterSwapListener)
    }

    const afterRequestListener = function (event) {
      // エラーが発生した場合か、タイムアウトした場合
      if (event.detail.xhr.status !== 200) {
        console.error('カレンダー更新に失敗しました:', event.detail.xhr.status)
        // リクエスト完了後にフラグをリセット
        window.calendarRefreshInProgress = false
      }
      // イベントリスナーを削除
      window.removeEventListener('htmx:afterRequest', afterRequestListener)
    }

    // イベントリスナーを追加
    window.addEventListener('htmx:afterSwap', afterSwapListener)
    window.addEventListener('htmx:afterRequest', afterRequestListener)

    // フラグのリセット用タイムアウト（万が一イベントが発火しない場合の保険）
    setTimeout(() => {
      if (window.calendarRefreshInProgress) {
        window.calendarRefreshInProgress = false
      }
    }, 5000)

    try {
      // htmxリクエスト送信
      htmx.ajax('GET', url, {
        target: '#calendar',
        swap: 'innerHTML'
      })
    } catch (error) {
      window.calendarRefreshInProgress = false
    }
  }

  /**
   * HX-Trigger ヘッダーを共通で処理
   * @param {XMLHttpRequest} xhr
   */
  function handleTrigger(xhr) {
    const trigHeader = xhr.getResponseHeader('HX-Trigger')
    if (!trigHeader) return

    let triggers
    try {
      triggers = JSON.parse(trigHeader)
    } catch {
      if (trigHeader.startsWith('openModal:')) {
        document.getElementById(trigHeader.split(':')[1])?.showModal()
      }
      if (trigHeader.startsWith('closeModal:')) {
        document.getElementById(trigHeader.split(':')[1])?.close()
      }
      return
    }

    // モーダル開閉
    if (triggers.openModal) {
      document.getElementById(triggers.openModal)?.showModal()
    }
    if (triggers.closeModal) {
      document.getElementById(triggers.closeModal)?.close()
    }

    // カレンダー再描画（登録／更新／削除後）
    // リフレッシュフラグとイベント処理の競合を避けるため、refreshUserAttendanceとrefreshAttendanceは
    // 一度に1つだけ処理し、少し遅延させて実行する
    if (triggers.refreshUserAttendance) {
      // トリガー処理用に専用の遅延関数を使用
      setTimeout(() => {
        const month = triggers.refreshUserAttendance.month
        refreshCalendar(month)
      }, 10)
      return // refreshAttendanceは処理しない
    }

    if (triggers.refreshAttendance) {
      // この処理は上記のrefreshUserAttendanceが実行されなかった場合のみ実行される
      setTimeout(() => {
        const month = triggers.refreshAttendance.month
        refreshCalendar(month)
      }, 10)
    }
  }

  // htmxリクエスト前に月情報を保存
  window.addEventListener('htmx:beforeRequest', function (e) {
    const elt = e.detail.elt
    // クリックされた要素がmonth_switcherのボタンかチェック
    if (elt.tagName === 'BUTTON' && elt.hasAttribute('hx-get')) {
      const url = new URL(elt.getAttribute('hx-get'), window.location.origin)
      const monthParam = url.searchParams.get('month')
      if (monthParam) {
        saveCurrentMonth(monthParam)
      } else if (elt.textContent.trim() === '今月') {
        // 「今月」ボタンの場合は現在の月を保存（サーバー側で判断）
        localStorage.removeItem('selectedMonth')
      }
    }
  })

  // コンテンツ置換後
  window.addEventListener('htmx:afterOnLoad', (e) => {
    // カレンダー更新中のフラグをリセット（念のため）
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    // URLに月の情報がある場合はlocalStorageに保存
    saveMonthFromUrl()
    handleTrigger(e.detail.xhr)
  })

  // 204 No Content などで置換が発生しないケース
  window.addEventListener('htmx:afterRequest', (e) => {
    // カレンダー更新中のフラグをリセット（念のため）
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }

    handleTrigger(e.detail.xhr)
  })

  // htmxのエラー発生時
  window.addEventListener('htmx:responseError', (e) => {
    console.error('htmx:responseError イベント発生:', e.detail.error)
    // カレンダー更新中のフラグをリセット
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }
  })

  // htmxのスワップエラー発生時
  window.addEventListener('htmx:swapError', (e) => {
    console.error('htmx:swapError イベント発生:', e.detail.error)
    // カレンダー更新中のフラグをリセット
    if (window.calendarRefreshInProgress) {
      window.calendarRefreshInProgress = false
    }
  })

  // ページ読み込み時
  document.addEventListener('DOMContentLoaded', () => {
    saveMonthFromUrl()

    // localStorageに月情報があり、かつURLに月情報がない場合は保存された月のカレンダーを読み込む
    const urlParams = new URLSearchParams(window.location.search)
    const monthInUrl = urlParams.get('month')
    const savedMonth = localStorage.getItem('selectedMonth')

    if (savedMonth && !monthInUrl && window.location.pathname.includes('/attendance')) {
      refreshCalendar(savedMonth)
    }
  })
})()
